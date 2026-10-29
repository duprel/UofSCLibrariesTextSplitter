import sys
from collections import namedtuple
#from enum import Enum
from pathlib import Path
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QComboBox,
                               QLabel, QLineEdit, QPushButton, 
                               QRadioButton, QHBoxLayout, QVBoxLayout, QGroupBox)
from  PySide6.QtCore import (Qt, Signal)

defaultRetentionPolicy = "Delete"

class TclPdfRetentionPolicy(QGroupBox):
  retentionPolicyChanged = Signal(str)

  def __init__(self, choice=defaultRetentionPolicy):
    self.choice = choice
    super().__init__("Retention Policy")
    self.initialize()

  def initialize(self):
    retention_vbox = QVBoxLayout(self)
    retention_descr = QLabel(
      (
      """Your input and output directories are different. What should """
      """be done with the original file in the input directory after """ 
      """the new version is placed in the output directory?"""
      )    
    )
    retention_descr.setWordWrap(True)
    retention_descr.setFixedWidth(430)
    retention_descr.setFixedHeight(100)
    retention_descr.setLineWidth(0)
    retention_vbox.addWidget(retention_descr)

    self.retain_original_rb = QRadioButton("Retain", self)
    self.retain_original_rb.setChecked(self.choice == "Retain")
    retention_vbox.addWidget(self.retain_original_rb)

    self.delete_original_rb = QRadioButton("Delete", self)
    self.delete_original_rb.setChecked(self.choice == "Delete")
    retention_vbox.addWidget(self.delete_original_rb)

    self.setLayout(retention_vbox)

    self.retain_original_rb.toggled.connect(self.retention_changed)
    self.delete_original_rb.toggled.connect(self.retention_changed)
    

  def retention_changed(self):
    if self.retain_original_rb.isChecked():
      self.choice = "Retain"
    else:
      self.choice = "Delete"

    self.retentionPolicyChanged.emit(self.choice)

__all__ = ['defaultRetentionPolicy',
           'TclPdfRetentionPolicy']

class MainWindow(QMainWindow):
  def __init__(self):
    self.central = QWidget()
    self.items = ["Enabled","Disabled"]
    super().__init__()
    layout = QVBoxLayout()
    self.retention_group = TclPdfRetentionPolicy(defaultRetentionPolicy)
    self.combo_box = QComboBox()
    self.combo_box.addItems(self.items)
    self.combo_box.currentIndexChanged.connect(self.index_changed)
    self.combo_box.currentTextChanged.connect(self.text_changed)

    self.reveal_current = QLabel()
    self.retention_group.retentionPolicyChanged.connect(self.show_current)

    layout.addWidget(self.retention_group)
    layout.addWidget(self.combo_box)
    layout.addWidget(self.reveal_current)

    self.central.setLayout(layout)
    self.setCentralWidget(self.central)

    self.show_current(self.retention_group.choice)

  def show_current(self, ev):
    self.reveal_current.setText(ev)

  def index_changed(self, i):
    if self.items[i] == "Enabled":
      self.retention_group.setEnabled(True)
    else:
      self.retention_group.setEnabled(False)

  def text_changed(self, s):
    if s == "Enabled":
      self.retention_group.setEnabled(True)
    else:
      self.retention_group.setEnabled(False)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())