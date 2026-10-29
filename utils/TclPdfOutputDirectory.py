import math 
import os
from dataclasses import dataclass
from pathlib import Path
from enum import Enum

from PySide6.QtCore import (Qt, QObject, Signal, QAbstractListModel, QModelIndex,
                            QThreadPool)
from PySide6.QtGui import QIcon, QAction
from PySide6.QtWidgets import QMenu

from utils.TclPdfBackgroundProcess import (TclPdfNumCoverPages, 
                                     TclPdfRmLeadingPages, 
                                     TclPdfSignals)


@dataclass
class TclPdfOutput:
  id: int
  filename: str
    
#  def contextMenu(self, parent):
#    menu = QMenu(parent)
#    menu.addAction(QAction("View"))
#    menu.addAction(QAction("Set Number of Cover Pages"))
#    if self.status == TclPdfInputStatus.UNCHECKED:
#      menu.addAction(QAction("Check for Cover Pages"))
#    return menu


class TclPdfOutputDirectory(QAbstractListModel):

  def __init__(self, settings=None, parent=None):
    self.settings = settings
    super().__init__()
    self.getFiles()

  def getFiles(self):
    if self.settings:
      directory = self.settings.value("out_directory")
      self.files = []
      if not directory:
        return
      index = 0
      for fname in sorted(Path(directory).glob("*.pdf", case_sensitive=False)):
        fpath = Path(fname)
        if (fpath.is_file() and
            not fpath.name.startswith('.')):
          input = TclPdfOutput(id=index, filename=fpath)
          self.files.append(input)
          index = index + 1

  def reload(self):
    self.beginResetModel()
    self.getFiles()
    self.endResetModel()

  def flags(self, index):
    return Qt.ItemFlag.ItemIsEnabled|Qt.ItemFlag.ItemIsSelectable

  def headerData(self):
    return(["filename"])

  def rowCount(self, parent=QModelIndex()):
    return(len(self.files))    

  def data(self, index, role=Qt.DisplayRole):
    row = index.row()
    if row < 0 or row >= self.rowCount():
      return None

    item = self.files[row]
    #print(f"row({row}) role({role}): {item}")
    if role == Qt.DisplayRole:
      return str(item.filename.name)
    elif role == Qt.DecorationRole:
      ui_dir = Path(__file__).resolve().parents[1]
      icon = QIcon(str(ui_dir/"ui"/"resources"/"icons"/"document-pdf.png"))
      return icon
    elif role == Qt.UserRole + 1:
      return item

    return None


__all__ = [
  TclPdfOutput,
  TclPdfOutputDirectory,
]    
