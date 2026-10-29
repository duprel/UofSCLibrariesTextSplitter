import math 
import os
from dataclasses import dataclass
from pathlib import Path
from enum import Enum

from PySide6.QtCore import (Qt, QObject, Signal, QAbstractListModel, QModelIndex,
                            QThreadPool)
from PySide6.QtGui import QIcon, QAction
from PySide6.QtWidgets import QMenu

from .TclPdfBackgroundProcess import (TclPdfNumCoverPages, 
                                     TclPdfRmLeadingPages, 
                                     TclPdfSignals)


class TclPdfInputStatus(Enum):
  UNCHECKED = 0
  CHECKED_KNOWN = 1
  CHECKED_UNKNOWN = 2
  MANUALLY_SET = 3
  PROCESSED = 4


@dataclass
class TclPdfInput:
  id: int
  filename: str
  status: TclPdfInputStatus = TclPdfInputStatus.UNCHECKED
  num_cover_pages: int | None = None

  def clearNumPages(self):
    self.num_cover_pages = None
    self.status = TclPdfInputStatus.UNCHECKED

  def setNumCoverPages(self, num):
    self.num_cover_pages = num
    self.status = TclPdfInputStatus.MANUALLY_SET

    
class TclPdfInputDirectory(QAbstractListModel):

  def __init__(self, settings=None, parent=None):
    self.settings = settings
    super().__init__()
    self.getFiles()

  def getFiles(self):
    if self.settings:
      directory = self.settings.value("in_directory")
      self.files = []
      if not directory:
        return
      index = 0
      for fname in sorted(Path(directory).glob("*.pdf", case_sensitive=False)):
        fpath = Path(fname)
        if (fpath.is_file() and
            not fpath.name.startswith('.')):
          input = TclPdfInput(id=index, filename=fpath, 
                              status=TclPdfInputStatus.UNCHECKED, 
                              num_cover_pages=None)
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
      match item.status:
        case TclPdfInputStatus.UNCHECKED:
          icon = QIcon(str(ui_dir/"ui"/"resources"/"icons"/"document-pdf.png"))
        case TclPdfInputStatus.CHECKED_KNOWN:
          icon = QIcon(str(ui_dir/"ui"/"resources"/"icons"/f"blue-document-number-{str(item.num_cover_pages)}.png"))
        case TclPdfInputStatus.CHECKED_UNKNOWN:
          icon = QIcon(str(ui_dir/"ui"/"resources"/"icons"/"exclamation-red-frame.png"))
        case TclPdfInputStatus.MANUALLY_SET:
          icon = QIcon(str(ui_dir/"ui"/"resources"/"icons"/f"document-number-{str(item.num_cover_pages)}.png"))
        case TclPdfInputStatus.PROCESSED:
          icon = QIcon(str(ui_dir/"ui"/"resources"/"icons"/"tick.png"))
      return icon
    elif role == Qt.UserRole + 1:
      return item

    return None

#class RunProcessesOverDirSignals(QObject):
#  finished = Signal(dict)
#  progress = Signal(int)
#  error = Signal(str)


class RunProcessesOverDir(QObject):
  threadpool = QThreadPool()
  threadpool.setMaxThreadCount(2)
  finished = Signal(dict)
  progress = Signal(int)
  error = Signal(str)

  def __init__(self):
    print(f"Max thread count is {self.threadpool.maxThreadCount()}")
    self.workers = []
    super().__init__()


class CheckNumCoverPages(RunProcessesOverDir):

  def __init__(self, inputDirectory=None):
    self.inputDirectory = inputDirectory
    self.file_list = []
    super().__init__()

  def processFiles(self):
    num_all_files = self.inputDirectory.rowCount()
    for index in range(num_all_files):
      input_index = self.inputDirectory.index(index,0)
      input_file = self.inputDirectory.data(input_index, Qt.UserRole + 1)
      if input_file.status == TclPdfInputStatus.UNCHECKED:
        self.file_list.append((input_file.filename, input_index))

    self.original_list_size = len(self.file_list)
    self.num_complete = 0
    
    for input_filename, input_index in self.file_list:
      worker = TclPdfNumCoverPages(input_filename, input_index)
      self.workers.append(worker)
      worker.signals.result.connect(self.fileResult)
      worker.signals.error.connect(self.fileError)
      self.threadpool.start(worker)

  def fileResult(self, result):
    index = result['identifier']
#    self.file_list[index.row()] = (result["file_path"], 
#                                   result["identifier"],
#                                   result["result"])
    self.num_complete = self.num_complete + 1
    completed = math.ceil(self.num_complete * 100 / self.original_list_size)
    print(f"progress: {completed}%")
    self.progress.emit(completed)
    print(f"result: {str(result)}")
    self.finished.emit(result)
    
  def fileError(self, error):
    pass

class RmLeadingPages(RunProcessesOverDir):

  def __init__(self, inputDirectory, settings):
    self.inputDirectory = inputDirectory
    self.settings = settings
    self.file_list = []
    super().__init__()

  def processFiles(self):
    num_all_files = self.inputDirectory.rowCount()
    for index in range(num_all_files):
      input_index = self.inputDirectory.index(index,0)
      input_file = self.inputDirectory.data(input_index, Qt.UserRole + 1)

      if ((input_file.status == TclPdfInputStatus.CHECKED_KNOWN
           or input_file.status == TclPdfInputStatus.MANUALLY_SET)
          and int(input_file.num_cover_pages) > 0):
        self.file_list.append((input_file.filename, input_index, input_file.num_cover_pages))

    self.original_list_size = len(self.file_list)
    self.num_complete = 0

    if (self.settings.value('in_directory') == self.settings.value('out_directory')
        and self.settings.value('overwrite_policy') == "Backup"):
      backup_extension = self.settings.value('backup_extension')
    else:
      backup_extension = None

    leave_original = self.settings.value('retention_policy') == "Retain"
    
    for input_filename, input_index, num_cover_pages in self.file_list:
      bname = os.path.basename(input_filename)
      outpath = os.path.join(self.settings.value('out_directory'), bname)
      worker = TclPdfRmLeadingPages(input_filename, outpath, 
                                    input_index, num_cover_pages,
                                    leave_original=leave_original,
                                    backup_extension=backup_extension)
      worker.signals.result.connect(self.fileResult)
      worker.signals.error.connect(self.fileError)
      print(f"Requesting threadpool start for {bname}")
      self.threadpool.start(worker)

  def fileResult(self, result):
    index = result['identifier']
#    self.file_list[index.row()] = (result["file_path"], 
#                                   result["identifier"],
#                                   result["result"])
    self.num_complete = self.num_complete + 1
    completed = math.ceil(self.num_complete * 100 / self.original_list_size)
    print(f"progress: {completed}%")
    self.progress.emit(completed)
    print(f"result: {str(result)}")
    self.finished.emit(result)
 
  def fileError(self, error):
    pass


__all__ = [
  TclPdfInputStatus,
  TclPdfInput,
  TclPdfInputDirectory,
  CheckNumCoverPages,
  RmLeadingPages,
]    
