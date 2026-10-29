from pathlib import Path
from PySide6.QtWidgets import (QWidget, QLabel, QLineEdit, QPushButton, 
                               QFileDialog, QHBoxLayout)
from  PySide6.QtCore import (Qt, QStandardPaths, Signal)
from PySide6.QtGui import (QIcon)

search_icon = "../resources/icons/search.png"

class TclSelectDirectoryWidget(QWidget):
  directorySelected = Signal(str)

  def __init__(self, start_path=None, label_text="Selected Directory"):
    self.label_text = label_text
    self.selected_path = start_path
    super().__init__()
    
    input_label = QLabel(self.label_text + ":")
    input_select_button = QPushButton("Select Directory", self)
    input_select_button.pressed.connect(self.handleSelect)
    self.input_select_line = QLineEdit()
    self.input_select_line.setMinimumWidth(150)
    self.input_select_line.setReadOnly(True)
    self.input_select_line.setAlignment(Qt.AlignmentFlag.AlignLeft)
    self.input_select_line.addAction(QIcon(search_icon), QLineEdit.ActionPosition.LeadingPosition) 
    self.input_select_line.setPlaceholderText(str(self.selected_path) 
                                              if self.selected_path
                                              else "<Press Select Button>") 
    input_hbox = QHBoxLayout()
    input_hbox.addWidget(input_label)
    input_hbox.addWidget(self.input_select_line)
    input_hbox.addWidget(input_select_button)
    self.setLayout(input_hbox)
    self.set_selected_path(self.selected_path)

  def handleSelect(self):
    if self.selected_path:
      dir = str(self.selected_path)
    else:
      dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation)

    dirname = QFileDialog.getExistingDirectory(self, "Open Directory", dir,
                                                  QFileDialog.ShowDirsOnly)
    if dirname:
        self.input_select_line.setText(dirname)
        self.set_selected_path(set_path=dirname)

  def set_selected_path(self, set_path=None):
    self.input_select_line.setPlaceholderText(str(set_path) 
                                                  if set_path
                                                  else "<Press Select Button>") 
    if set_path:
      selected_path = Path(set_path)
      if not selected_path.is_dir():
        selected_path = selected_path.parent
      self.selected_path = selected_path
      self.directorySelected.emit(str(self.selected_path))
    

#
#  def handleSelect(self):
#    dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation)
#    dirname = QFileDialog.getExistingDirectory(self, "Open Directory", dir,
#                                                  QFileDialog.ShowDirsOnly)
#    if dirname:
#        self.input_select_line.setText(dirname)

__all__ = ["TclSelectDirectoryWidget"]
