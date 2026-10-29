import os, sys, time
from pathlib import Path
from PySide6.QtWidgets import (QApplication, QDialog, QLabel, QWidget, QListWidget,
    QDialogButtonBox, QGroupBox, QRadioButton, QListWidgetItem, QListView,
    QProgressBar, QLineEdit, QPushButton, QTextEdit, QMenu, QSpinBox,
    QComboBox, QFileDialog, QHBoxLayout, QVBoxLayout, QMainWindow, QStatusBar)
from PySide6.QtCore import (QCoreApplication, Qt, Signal, QSettings, QStandardPaths,
                            QSize, QPoint)
from PySide6.QtGui import QAction, QIcon
from .TclPdfSettingsDialog import PdfSettings, PdfSettingsDialog
from utils.TclPdfOutputDirectory import (TclPdfOutputDirectory)
from .TclPdfViewDialog import TclPdfViewDialog

ui_dir = Path(__file__).resolve().parents[1]

document_icon_path  = str(ui_dir/"resources"/"icons"/"document-pdf.png")

class TclPdfOutputDirectoryWidget(QWidget):

  def __init__(self, settings):
    super().__init__()
    self.current_index = None
    self.async_operations = False
    self.settings = settings
    self.initializeUI()

  def initializeUI(self):
    """Set up the application's GUI."""

    self.setUpMainWindow()
    self.createActions()
    self.show()
    
  def setUpMainWindow(self):
    if self.settings.value("out_directory", None):
      output_dir_text = str(self.settings.value("out_directory"))
    else:
      output_dir_text = "<<Go to settings to set the PDF output directory>>"

    self.output_label = QLabel(f"Output Directory: {output_dir_text}")

    self.list_view = QListView()
    self.list_model = TclPdfOutputDirectory(self.settings)
    self.list_view.setModel(self.list_model)
    self.list_view.setContextMenuPolicy(Qt.CustomContextMenu)
    self.list_view.customContextMenuRequested.connect(self.showContextMenu)

    vbox = QVBoxLayout()
    vbox.addWidget(self.output_label)
    vbox.addWidget(self.list_view)
    self.setLayout(vbox)

  def reloadPdfs(self):
    output_dir_text = str(self.settings.value("out_directory"))
    self.output_label.setText(f"Output Directory: {output_dir_text}")
    self.list_model.reload()

  def showContextMenu(self, pos: QPoint):
    index = self.list_view.indexAt(pos)
    self.current_index = index

    menu = QMenu(self)
    if index.isValid():
      item = self.list_model.data(index, Qt.UserRole + 1)
      menu.addAction(self.view_act)
      menu.exec(self.list_view.viewport().mapToGlobal(pos))

  def createActions(self):
    self.view_act = QAction(QIcon(document_icon_path), "View")
    self.view_act.triggered.connect(self.viewSelection)
    self.list_view.doubleClicked.connect(self.itemDoubleClicked)

  def itemDoubleClicked( self, index):
    self.current_index = index
    self.viewSelection()

  def viewSelection(self):
    item = self.list_model.data(self.current_index, Qt.UserRole + 1)
    self.dialog = TclPdfViewDialog(self, self.settings, str(item.filename))
    self.dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
    self.dialog.exec()
    
