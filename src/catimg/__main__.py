#!/usr/bin/env python

"""
Prints images in the terminal.

Usage: catimg.py <image...>
"""

from dataclasses import dataclass
import os
from typing import Tuple, List
import PIL.Image
import sys
import termios

TERMINAL_ASPECT_RATIO = 1/2

def ansi_color(r, g, b):
  return "\033[38;2;{};{};{}m".format(r, g, b)

@dataclass
class Image:
  original: PIL.Image
  size: Tuple[int, int]
  pixels: List[Tuple[int, int, int]]

def open_image(path, hint_resize):
  img = PIL.Image.open(path)
  
  (letterbox_width, letterbox_height) = (0, 0)
  (fit_width, fit_height) = hint_resize
  (img_width, img_height) = img.size
  r = min(fit_width / img_width * TERMINAL_ASPECT_RATIO, fit_height / img_height)
  letterbox_width = int(img_width * r * 2)
  letterbox_height = int(img_height * r * 2)
  hint_resize = (letterbox_width, letterbox_height)
  resized_img = img.resize(hint_resize, PIL.Image.Resampling.BICUBIC)

  return Image(img, resized_img.size, list(resized_img.getdata()))

def print_image(image, fit_size):
  (fit_width, fit_height) = fit_size
  (img_width, img_height) = image.size

  (letterbox_width, letterbox_height) = (0, 0)
  r = min(fit_width / img_width * TERMINAL_ASPECT_RATIO, fit_height / img_height)
  letterbox_width = int(img_width / TERMINAL_ASPECT_RATIO * r)
  letterbox_height = int(img_height * r)
  txt = ''
  for y in range(letterbox_height):
    for x in range(letterbox_width):
      sx = x * img_width // letterbox_width
      sy = y * img_height // letterbox_height
      (r, g, b, *_) = image.pixels[sy * image.size[0] + sx]
      txt += ansi_color(r, g, b) + "█"
    txt += "\n"
  txt += "\033[0m"
  print(txt, end='')


def print_image_file(path, fit_size):
  image = open_image(path, fit_size)
  print(">", path, "{}x{}".format(*image.original.size))
  print_image(image, fit_size)


def main():
  sys.argv.pop(0)
  if len(sys.argv) == 0:
    print("Usage: catimg.py <image...>")
    sys.exit(1)

  print_size = os.get_terminal_size()
  print_size = (print_size[0], print_size[1]-2)

  image_files = []
  for file_name in sys.argv:
    if os.path.isfile(file_name):
      image_files.append(file_name)
    elif os.path.isdir(file_name):
      for file in os.listdir(file_name):
        image_files.append(os.path.join(file_name, file))
    else:
      print("catimg.py: {}: No such file or directory".format(file_name), file=sys.stderr)
    
  try:
    tty_in = os.open("/dev/tty", os.O_RDONLY)
    tty_out = os.open("/dev/tty", os.O_WRONLY)
    old_term = termios.tcgetattr(tty_in)
    new_term = termios.tcgetattr(tty_in)
    new_term[3] = new_term[3] & ~termios.ICANON & ~termios.ECHO & ~termios.ICRNL
    new_term[0] = new_term[0] & ~termios.ICRNL
    termios.tcsetattr(tty_in, termios.TCSAFLUSH, new_term)

    continue_without_prompt = False
    for (i, img_file) in enumerate(image_files):
      print_image_file(img_file, print_size)
      while not continue_without_prompt and i != len(image_files)-1:
        usr_cmd = os.read(tty_in, 1)
        if usr_cmd == b'q':
          return
        elif usr_cmd == b'\n' or usr_cmd == b'\r':
          break
        elif usr_cmd == b' ':
          continue_without_prompt = True
          break

  finally:
    termios.tcsetattr(tty_out, termios.TCSAFLUSH, old_term)


if __name__ == '__main__':
  main()
