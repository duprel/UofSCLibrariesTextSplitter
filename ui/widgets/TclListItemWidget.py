import sys
from collections import namedtuple
from PySide6.QtWidgets import (QWidget, QMenu, QListWidget, QListWidgetItem,
                               QLabel, QLineEdit, QRadioButton, QHBoxLayout, 
                               QVBoxLayout, QGroupBox)
from  PySide6.QtCore import (Qt, Signal)

class TclPdfListItemWidget(QListWidgetItem):
