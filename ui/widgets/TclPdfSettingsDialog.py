import os, sys, time
from collections import namedtuple
from PySide6.QtWidgets import (QApplication, QDialog, QLabel, QWidget,
    QDialogButtonBox, QGroupBox, QRadioButton,
    QProgressBar, QLineEdit, QPushButton, QTextEdit, 
    QComboBox, QFileDialog, QHBoxLayout, QVBoxLayout, QMainWindow, QStatusBar)
from PySide6.QtCore import QCoreApplication, Qt, Signal, QSettings, QStandardPaths
from PySide6.QtGui import (QAction, QIcon)
from .TclSelectDirectoryWidget import TclSelectDirectoryWidget
from .TclPdfOverwritePolicy import defaultOverwritePolicy,PdfOverwritePolicy,TclPdfOverwritePolicy
from .TclPdfRetentionPolicy import defaultRetentionPolicy,TclPdfRetentionPolicy

PdfSettings = namedtuple("PdfSettings", ["in_directory",
                                         "out_directory",
                                         "overwrite_policy",
                                         "backup_extension",
                                         "retention_policy"])

class PdfSettingsDialog(QDialog):
  pdfSettingsAccepted = Signal(PdfSettings)
  def __init__(self, parent, settings=None):
    if settings:
      self.in_directory = settings.value("in_directory", QStandardPaths.writableLocation(QStandardPaths.StandardLocation.HomeLocation))
      self.out_directory = settings.value("out_directory", QStandardPaths.writableLocation(QStandardPaths.StandardLocation.HomeLocation))
      self.overwrite_policy = settings.value("overwrite_policy", defaultOverwritePolicy.policy)
      self.backup_extension = settings.value("backup_extension", defaultOverwritePolicy.backup_extension)
      self.retention_policy = settings.value("retention_policy", defaultRetentionPolicy)
      self.pdf_settings = None
    else:
      self.in_directory = None
      self.out_directory = None
      self.overwrite_policy = None
      self.backup_extension = None
      self.retention_policy = None
      self.pdf_settings = None

    super().__init__(parent)
    self.settings = settings
    self.setModal(True)
    self.setSizeGripEnabled(True)
    self.initializeUI()

  def initializeUI(self):
    self.setMinimumWidth(700)
    self.setWindowTitle("Settings")
    self.setUpWindow()

  def setUpWindow(self):
    buttons = (QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
    
    layout = QVBoxLayout()
    self.in_select_widget = TclSelectDirectoryWidget(start_path=self.in_directory, 
                                                     label_text="Pick a Directory")
    self.out_select_widget = TclSelectDirectoryWidget(start_path=self.out_directory, 
                                                      label_text="Pick a Directory")
    self.overwrite_policy_widget = TclPdfOverwritePolicy(PdfOverwritePolicy(
      self.overwrite_policy if self.overwrite_policy else defaultOverwritePolicy.policy,
      self.backup_extension if self.backup_extension else defaultOverwritePolicy.backup_extension
    ))
    self.retention_policy_widget = TclPdfRetentionPolicy(self.retention_policy 
                                                         if self.retention_policy 
                                                         else defaultRetentionPolicy)
    self.button_box = QDialogButtonBox(buttons)

    layout.addWidget(self.in_select_widget)
    layout.addWidget(self.out_select_widget)
    layout.addWidget(self.overwrite_policy_widget)
    layout.addWidget(self.retention_policy_widget)
    layout.addWidget(self.button_box)
    self.setLayout(layout)

    self.in_select_widget.directorySelected.connect(self.set_in_directory)
    self.out_select_widget.directorySelected.connect(self.set_out_directory)
    self.overwrite_policy_widget.overwritePolicyChanged.connect(self.set_overwrite_policy)
    self.retention_policy_widget.retentionPolicyChanged.connect(self.set_retention_policy)
    self.button_box.accepted.connect(self.accept)
    self.button_box.rejected.connect(self.reject)

    self.check_enabling()

  def set_in_directory(self, ev):
    self.in_directory = ev
    self.check_enabling()

  def set_out_directory(self, ev):
    self.out_directory = ev
    self.check_enabling()

  def set_overwrite_policy(self, ev):
    self.overwrite_policy = ev.policy
    self.backup_extension = ev.backup_extension
    self.check_enabling()

  def set_retention_policy(self, ev):
    self.retention_policy = ev
    self.check_enabling()

  def check_enabling(self):
    if self.in_directory and self.out_directory:
      if self.in_directory == self.out_directory:
        self.overwrite_policy_widget.setEnabled(True)
        self.retention_policy_widget.setEnabled(False)
      else:
        self.overwrite_policy_widget.setEnabled(False)
        self.retention_policy_widget.setEnabled(True)
    else:
      self.overwrite_policy_widget.setEnabled(False)
      self.retention_policy_widget.setEnabled(False)
  
  def accept(self):
    self.pdf_settings = PdfSettings(self.in_directory,
                                   self.out_directory,
                                   self.overwrite_policy,
                                   self.backup_extension,
                                   self.retention_policy)
    self.pdfSettingsAccepted.emit(self.pdf_settings)
    self.done(QDialog.DialogCode.Accepted)
    super().accept()

  def reject(self):
    self.done(QDialog.DialogCode.Rejected)
    super().reject()

  def pdfSettings(self):
    return self.pdf_settings
    
__all__ = ['PdfSettings', 'PdfSettingsDialog']