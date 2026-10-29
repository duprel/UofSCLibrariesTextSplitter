from PySide6.QtPdf import QPdfDocument 
from PySide6.QtPdfWidgets import QPdfView
from PySide6.QtWidgets import (QDialog, QLabel, QPushButton, QVBoxLayout, 
                               QHBoxLayout)
from PySide6.QtCore import Qt, QSize, QPoint
from PySide6.QtGui import QIcon

previous_icon = "../resources/icons/blue-document-page-previous.png"
next_icon     = "../resources/icons/blue-document-page-next.png"

class TclPdfViewDialog(QDialog):

  def __init__(self, parent, settings, in_file_path):
    self.in_file_path = in_file_path
    self.settings = settings
    super().__init__(parent)

    self.document = QPdfDocument(self)
    self.document.load(self.in_file_path)
    self.pdf_view = QPdfView(self)
    
    h_layout = QHBoxLayout()
    h_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
    self.prev_button = QPushButton("Previous")
    self.prev_button.setFixedWidth(120)
    self.prev_button.setIcon(QIcon(previous_icon))
    self.prev_button.setIconSize(QSize(32,32))
    self.prev_button.clicked.connect(self.previous_page)
    h_layout.addWidget(self.prev_button)

    self.next_button = QPushButton("Next")
    self.next_button.setFixedWidth(120)
    self.next_button.setIcon(QIcon(next_icon))
    self.next_button.setIconSize(QSize(32,32))
    self.next_button.clicked.connect(self.next_page)
    h_layout.addWidget(self.next_button)

    v_layout = QVBoxLayout()
    v_layout.addLayout(h_layout)
    v_layout.addWidget(self.pdf_view)

    self.setLayout(v_layout)

    self.pdf_view.setDocument(self.document)
    self.geometry = self.settings.value("view_geometry")
    if self.geometry:
      self.restoreGeometry(self.geometry)
    else:
      self.setGeometry(100,0,800,600)

  def previous_page(self):
    print("previous page")
    navigator = self.pdf_view.pageNavigator()
    current = navigator.currentPage()
    if current > 0:
      #self.navigator.jump(current-1, self.pdf_view.location(), self.navigator.currentZoom())
      navigator.jump(current-1, QPoint(), navigator.currentZoom())

  def next_page(self):
    print("next page")
    navigator = self.pdf_view.pageNavigator()
    current = navigator.currentPage()
    count = self.document.pageCount()
    if current < count-1:
      #self.navigator.jump(current+1, self.pdf_view.location(), self.navigator.currentZoom())
      navigator.jump(current+1, QPoint(), navigator.currentZoom())

  def closeEvent(self, ev):
    self.geometry = self.saveGeometry()
    self.settings.setValue("view_geometry", self.geometry)
    super().closeEvent(ev)
