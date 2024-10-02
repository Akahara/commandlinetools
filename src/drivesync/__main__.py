import itertools
import pathlib
import logging
import json
import shutil
import sys
from . import difftool
from .googledrive import GDrive, GDriveFile
from .common import Common

DRIVESYNC_FILE_NAME = 'drivesync.json'
STATE_FILE_NAME = 'drivestate.txt'
DRY_ATTEMPT = False

"""
Usage:

Setup:
. Go to https://console.cloud.google.com and create a new project
. Select that project and create a new credential with a key, save the key file
. Enable the google drive api service
. Run this script from 
"""

logger = logging.getLogger()
logger.setLevel(logging.INFO)

class DriveSync:
    local_path = None
    settings_file = None
    gdrive = None
    exluded_files = [STATE_FILE_NAME]
    gdrive_root = None

    def __init__(self, local_path):
        self.local_path = local_path
        self.settings_file = pathlib.Path(local_path, DRIVESYNC_FILE_NAME)
        
    def init(self):
        if not self.settings_file.is_file():
            raise Exception("drivesync.txt did not exist, run with 'init' to create it")
        
        settings = json.loads(self.settings_file.read_text())
        if 'excluded' in settings:
            self.exluded_files += [str(l) for l in settings['excluded']]
        if 'sync-name' not in settings:
            raise Exception("sync-name not in drivesync.txt")

        self.gdrive = GDrive(pathlib.Path(self.local_path, settings['credentials']))
        
        remote_root = GDriveFile.get_root(self.gdrive)
        sync_root_name = settings['sync-name']
        sync_root = remote_root.get_child(sync_root_name)
        if sync_root is None:
            print(f"Creating root directory {sync_root_name}")
            self.gdrive_root = remote_root.mkdir(sync_root_name)
            shared_users = settings["shared"]
            if shared_users is not None:
                for usr in shared_users:
                    self.gdrive.grant_user_permissions(self.gdrive_root.id, usr)
        else:
            if not sync_root.is_directory:
                raise Exception(f"sync root '{sync_root_name}' is not a directory")
            self.gdrive_root = sync_root
        

    def fetch_remote_state(self):
        remote_state_file = self.gdrive_root.get_child(STATE_FILE_NAME)
        if remote_state_file is None:
            return []
        remote_state_file_local_copy = remote_state_file.download()
        return difftool.parse_state(remote_state_file_local_copy.read_text())

    def load_local_states(self):
        local_state_file = pathlib.Path(self.local_path, STATE_FILE_NAME)
        last_sync_state = []
        if local_state_file.is_file():
            last_sync_state = difftool.parse_state(local_state_file.read_text())
            last_sync_state = difftool.remove_ignored(last_sync_state, self.exluded_files)
        
        current_state = difftool.read_local_files(self.local_path)
        current_state = difftool.remove_ignored(current_state, self.exluded_files)
        
        return (local_state_file, last_sync_state, current_state)

    def sync_push(self):
        (local_state_file, last_sync_state, current_state) = self.load_local_states()
        
        applied_diff = difftool.diff_states(last_sync_state, current_state)
        (new, removed, changed) = applied_diff

        if len(new) == 0 and len(removed) == 0 and len(changed) == 0:
            print("No diff")
            return

        removed.sort(reverse=True)
        new.sort()

        if DRY_ATTEMPT:
            return print(f"{new=}\n{removed=}\n{changed=}")

        # remove old files
        for f in removed:
            (parent, file) = self.gdrive_root.get_deep(f.path)
            if file is not None:
                print(f"Removing remote {f.path}")
                file.remove()
            else:
                print(f"Removing remote {f.path} - already absent")

        # upload new files and create new directories
        for f in new:
            (parent, file) = self.gdrive_root.get_deep(f.path, mkdir_if_missing=True)
            file_name = pathlib.Path(f.path).name
            local_file = pathlib.Path(self.local_path, f.path)
            if f.is_directory:
                print(f"Creating remote {f.path}/")
                parent.mkdir(file_name)
            else:
                print(f"Uploading remote {f.path}")
                parent.upload_file(file_name, local_file)

        # upload changed files
        for f in changed:
            # assuming no file became a directory
            (parent, file) = self.gdrive_root.get_deep(f.path, mkdir_if_missing=True)
            file_name = pathlib.Path(f.path).name
            print(f"Uploading remote {f.path}")
            parent.upload_file(file_name, f.path)

        # update the remote state locally
        local_state_file.write_text(difftool.serialize_state(current_state))

        # update remote state
        remote_state = self.fetch_remote_state()
        remote_state = difftool.merge_diff(remote_state, applied_diff)
        remote_state_file_local_copy = Common.get_temp_file('txt')
        remote_state_file_local_copy.write_text(difftool.serialize_state(remote_state))
        self.gdrive_root.upload_file(STATE_FILE_NAME, remote_state_file_local_copy)
        print('Ending sync')

    def sync_pull(self):
        remote_state = self.fetch_remote_state()
        remote_state = difftool.remove_ignored(remote_state, self.exluded_files)
        (local_state_file, last_sync_state, current_state) = self.load_local_states()
        
        applied_diff = difftool.diff_states(last_sync_state, remote_state)
        (new, removed, changed) = applied_diff

        if len(new) == 0 and len(removed) == 0 and len(changed) == 0:
            print("No diff")
            return
        
        removed.sort(reverse=True)
        new.sort()
        
        if DRY_ATTEMPT:
            return print(f"{new=}\n{removed=}\n{changed=}")

        # remove old files
        for f in removed:
            print(f"Removing local {f.path}")
            fpath = pathlib.Path(self.local_path, f.path)
            if fpath.is_dir():
                shutil.rmtree(str(fpath))
            else:
                fpath.unlink()

        # download new and updated files
        for f in itertools.chain(new, changed):
            (parent, file) = self.gdrive_root.get_deep(f.path)
            local_path = pathlib.Path(self.local_path, f.path)
            if file is None:
                print(f"Tried to download {f.path} but file does not exist on remote")
            else:
                print(f"Downloading local {f.path}")
                local_path.parent.mkdir(parents=True, exist_ok=True)
                if local_path.exists():
                    local_path.unlink()
                if file.is_directory:
                    local_path.mkdir()
                else:
                    file.download().rename(local_path)

        # update local state
        current_state = difftool.merge_diff(current_state, applied_diff)
        local_state_file.write_text(difftool.serialize_state(current_state))

    def full_wipe(self):
        if input("Do a full wipe? (yes)") == 'yes':
            for f in self.gdrive.list_folder():
                print('deleting', f)
                self.gdrive.delete_files(f['id'])


def main():
    global DRY_ATTEMPT
    
    mode = '' if len(sys.argv) < 2 else sys.argv[1]
    DRY_ATTEMPT = '--dry' in sys.argv
    if mode not in ['init', 'pull', 'push', 'wipe']:
        print('Usage: <init|pull|push|wipe>')
        return
        
    sync = DriveSync('.')

    if mode == 'init':
        if sync.settings_file.is_file():
            print("Already a drivesync directory")
        else:
            sync.settings_file.write_text('{\n  "sync-name": <foldername>,\n  "credentials": "crendentials.json",\n  "excluded": [],\n  "shared": [ <yourmail@gmail.com> ]\n}')
            print(f"Initialized a drivesync directory, fill in {DRIVESYNC_FILE_NAME} and run with push")
        return

    sync.init()

    Common.setup()
    if mode == 'pull':
        sync.sync_pull()
    elif mode == 'push':
        sync.sync_push()
    elif mode == 'wipe':
        sync.full_wipe()
    Common.teardown()
