import math 
import os
from dataclasses import dataclass, field
from typing import ClassVar
from pathlib import Path
from enum import Enum

from PySide6.QtCore import (Qt, QObject, Signal, QAbstractListModel, QModelIndex,
                            QThreadPool)
from PySide6.QtGui import QIcon, QAction
from PySide6.QtWidgets import QMenu

from .TclBackgroundProcess import (TclCheckStatusOfInputFile, 
                                     TclProcessInputFile, 
                                     TclSignals)

ui_dir = Path(__file__).resolve().parents[1]

document_icon_path  = str(ui_dir/"resources"/"icons"/"document-pdf.png")
pencil_icon_path    = str(ui_dir/"resources"/"icons"/"pencil.png")
eraser_icon_path    = str(ui_dir/"resources"/"icons"/"eraser.png")
lightning_icon_path = str(ui_dir/"resources"/"icons"/"lightning.png")

class TclInputStatus(Enum):
  UNCHECKED = 0
  CHECKED_KNOWN = 1
  CHECKED_UNKNOWN = 2
  MANUALLY_SET = 3
  PROCESSED = 4

@dataclass
class TclInput:
  id: int
  filename: str
  status: TclInputStatus = TclInputStatus.UNCHECKED
  contents: dict = field(default_factory=dict)

  DOCUMENT_ICON:      ClassVar[str] = "document-pdf.png"
  EDIT_ICON:          ClassVar[str] = "pencil.png"
  CLEAR_ICON:         ClassVar[str] = "eraser.png"
  PROCESS_ICON:       ClassVar[str] = "lightning.png"
  UNCHECKED_ICON:     ClassVar[str] = "document-pdf.png"
  STATUS_CONTENT_TAG: ClassVar[str] = "<<STATUSCONTENT>>"
  KNOWN_ICON:         ClassVar[str] = "blue-document-number-<<statusContent>>.png"
  UNKNOWN_ICON:       ClassVar[str] = "exclamation-red-frame.png"
  SET_ICON:           ClassVar[str] = "document-number-<<statausContent>>.png"
  PROCESSED_ICON:     ClassVar[str] = "tick.png"

  @classmethod
  def statusContentKey(cls):
    pass

  @classmethod
  def iconDirectory(cls):
    return "ui/resources/icons"

  def statusContentIsKnown(self):
    pass

  def statusContentCanBeProcessed(self):
    pass

  def iconNameForStatus(self, status):
    match self.status:
      case TclInputStatus.UNCHECKED:
        name = UNCHECKED_ICON
      case TclInputStatus.CHECKED_KNOWN:
        name = KNOWN_ICON
      case TclInputStatus.CHECKED_UNKNOWN:
        name = UNKNOWN_ICON
      case TclInputStatus.MANUALLY_SET:
        name = SET_ICON
      case TclInputStatus.PROCESSED:
        name = PROCESSED_ICON

    if name.find(self.STATUS_CONTENT_TAG) == -1:
      icon_name = name
    else:
      icon_name = name.replace(self.STATUS_CONTENT_TAG, self.getStatusContent())  
    return icon_name

  def iconForStatus(self):
    return QIcon(self.iconDirectory() + "/" + self.iconNameForStatus(self.status))

  def getStatusContent(self):
    return self.contents.get(self.statusContentKey(), None)

  def setStatusContent(self, val):
    self.contents[self.statusContentKey()] = val
    self.status = TclInputStatus.MANUALLY_SET

  def clearStatusContent(self):
    self.contents[self.statusContentKey()] = None
    self.status = TclInputStatus.UNCHECKED


class TclInputDirectory(QAbstractListModel):
  INPUT_CLASS = TclInput
  GLOB_PATTERN = "*"

  @classmethod
  def iconDirectory(cls):
    return "ui/resources/icons"

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
      for fname in sorted(Path(directory).glob(self.GLOB_PATTERN, case_sensitive=False)):
        fpath = Path(fname)
        if (fpath.is_file() and
            not fpath.name.startswith('.')):
          input = self.INPUT_CLASS(id=index, filename=fpath, 
                                  status=TclInputStatus.UNCHECKED, 
                                  contents={})
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
    if role == Qt.DisplayRole:
      return str(item.filename.name)
    elif role == Qt.DecorationRole:
      return item.iconForStatus()
    elif role == Qt.UserRole + 1:
      return item

    return None


class TclRunProcessesOverDir(QObject):
  threadpool = QThreadPool()
  threadpool.setMaxThreadCount(2)
  finished = Signal(dict)
  progress = Signal(int)
  error = Signal(str)

  def __init__(self):
    print(f"Max thread count is {self.threadpool.maxThreadCount()}")
    self.workers = []
    super().__init__()


class TclCheckStatusOfInputFiles(TclRunProcessesOverDir):

  def __init__(self, inputDirectory=None):
    self.inputDirectory = inputDirectory
    self.file_list = []
    super().__init__()

  def processFiles(self):
    num_all_files = self.inputDirectory.rowCount()
    for index in range(num_all_files):
      input_index = self.inputDirectory.index(index,0)
      input_file = self.inputDirectory.data(input_index, Qt.UserRole + 1)
      if input_file.status == TclInputStatus.UNCHECKED:
        self.file_list.append((input_file.filename, input_index))

    self.original_list_size = len(self.file_list)
    self.num_complete = 0
    
    for input_filename, input_index in self.file_list:
      worker = TclCheckStatusOfInputFile(input_filename, input_index)
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

class TclProcessInputFiles(TclRunProcessesOverDir):

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

      if ((input_file.status == TclInputStatus.CHECKED_KNOWN
           or input_file.status == TclInputStatus.MANUALLY_SET)
          and input_file.statusContentCanBeProcessed()):
        self.file_list.append((input_file.filename, input_index, input_file.getStatusContent()))

    self.original_list_size = len(self.file_list)
    self.num_complete = 0

    if (self.settings.value('in_directory') == self.settings.value('out_directory')
        and self.settings.value('overwrite_policy') == "Backup"):
      backup_extension = self.settings.value('backup_extension')
    else:
      backup_extension = None

    leave_original = self.settings.value('retention_policy') == "Retain"
    
    for input_filename, input_index, status_content in self.file_list:
      bname = os.path.basename(input_filename)
      outpath = os.path.join(self.settings.value('out_directory'), bname)
      options = {'status_content': status_content}
      worker = TclProcessInputFile(input_filename, outpath, input_index, 
                                   leave_original=leave_original,
                                   backup_extension=backup_extension,
                                   options=options)
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
  TclInputStatus,
  TclInput,
  TclInputDirectory,
  TclCheckStatusOfInputFiles,
  TclProcessInputFiles,
]    
