import sys
from collections import namedtuple
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QComboBox,
                               QLabel, QLineEdit, QRadioButton, QHBoxLayout, 
                               QVBoxLayout, QGroupBox)
from  PySide6.QtCore import (Qt, Signal)

PdfOverwritePolicy = namedtuple('PdfOverwritePolicy', ['policy', 'backup_extension'])
defaultOverwritePolicy = PdfOverwritePolicy("Backup", ".bak")

class TclPdfOverwritePolicy(QGroupBox):
    overwritePolicyChanged = Signal(PdfOverwritePolicy)

    def __init__(self, policy=defaultOverwritePolicy):
        self.policy = policy
        super().__init__("Overwrite Policy")
        self.initialize()

    def initialize(self):
      overwrite_vbox = QVBoxLayout(self)
      overwrite_descr = QLabel(
        (
        """Your input and output directories are the same. You must specify an """
        """overwrite policy. Choose "Overwrite Originals" to replace original """
        """Pdf file. Choose "Backup Originals" to create backup of original before """
        """replacing with new Pdf file."""
        )
      )    
      overwrite_descr.setWordWrap(True)
      overwrite_descr.setFixedWidth(430)
      overwrite_descr.setFixedHeight(100)
      overwrite_descr.setLineWidth(0)
      overwrite_vbox.addWidget(overwrite_descr)

      self.replace_original_rb = QRadioButton("Overwrite", self)
      self.replace_original_rb.setChecked(self.policy.policy == "Overwrite")
      overwrite_vbox.addWidget(self.replace_original_rb)

      self.backup_original_rb = QRadioButton("Backup", self)
      self.backup_original_rb.setChecked(self.policy.policy == "Backup")
      overwrite_vbox.addWidget(self.backup_original_rb)

      backup_extension_group = QHBoxLayout()
      backup_label = QLabel("Backup Extension:")
      self.backup_extension = QLineEdit()
      
      self.backup_extension.setText(self.policy.backup_extension)
      self.backup_extension.setInputMask(".NNNnnnnnnn;_")
      backup_extension_group.addWidget(backup_label)
      backup_extension_group.addWidget(self.backup_extension)

      overwrite_vbox.addLayout(backup_extension_group)
      self.setLayout(overwrite_vbox)

      self.replace_original_rb.toggled.connect(self.policy_changed)
      self.backup_original_rb.toggled.connect(self.policy_changed)
      self.backup_extension.editingFinished.connect(self.policy_changed)

    def policy_changed(self):
      if self.replace_original_rb.isChecked():
        self.policy = PdfOverwritePolicy("Overwrite",
                                         self.backup_extension.text())
        self.backup_extension.setEnabled(False)
      else:
        self.policy = PdfOverwritePolicy("Backup",
                                         self.backup_extension.text())
        self.backup_extension.setEnabled(True)

      self.overwritePolicyChanged.emit(PdfOverwritePolicy(self.policy.policy,
                                                          self.policy.backup_extension))
       
__all__ = ['PdfOverwritePolicy',
           'defaultOverwritePolicy', 
           'TclPdfOverwritePolicy']
      
class MainWindow(QMainWindow):
  def __init__(self):
    self.central = QWidget()
    self.items = ["Enabled","Disabled"]
    super().__init__()
    layout = QVBoxLayout()
    self.overwrite_group = TclPdfOverwritePolicy(defaultOverwritePolicy)
    self.combo_box = QComboBox()
    self.combo_box.addItems(self.items)
    self.combo_box.currentIndexChanged.connect(self.index_changed)
    self.combo_box.currentTextChanged.connect(self.text_changed)

    self.reveal_current = QLabel()
    self.overwrite_group.overwritePolicyChanged.connect(self.show_current)

    layout.addWidget(self.overwrite_group)
    layout.addWidget(self.combo_box)
    layout.addWidget(self.reveal_current)

    self.central.setLayout(layout)
    self.setCentralWidget(self.central)

    self.show_current(self.overwrite_group.policy)

  def show_current(self, ev):
    self.reveal_current.setText(str(ev))

  def index_changed(self, i):
    if self.items[i] == "Enabled":
      self.overwrite_group.setEnabled(True)
    else:
      self.overwrite_group.setEnabled(False)

  def text_changed(self, s):
    if s == "Enabled":
      self.overwrite_group.setEnabled(True)
    else:
      self.overwrite_group.setEnabled(False)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())