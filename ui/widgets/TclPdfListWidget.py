import sys
from pathlib import Path
from PySide6.QtWidgets import (QListWidget, QLabel )
from PySide6.QtCore import (Qt, Signal)

class TclPdfListWidget(QListWidget):

  def __init__(self, input_directory=None, output_directory=None):
    self.input_directory = input_directory
    self.output_directory = output_directory
    super().__init__()
    self.initializeUI()

  def initializeUI(self):
    if self.input_directory:
      input_dir_text = str(self.input_directory)
    else:
      input_dir_text = "Go to settings to set the PDF input directory"

    if self.output_directory:
      output_dir_text = str(self.output_directory)
    else:
      output_dir_text = "Go to settings to set the PDF output directory"

    input_label = QLabel(input_dir_text)
    output_label = QLabel(output_dir_text)







  