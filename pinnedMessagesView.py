# Copyright (C) 2024 Mael FEURGARD <mael.feurgard@enac.fr>
# 
# This file is part of messages_python.
# 
# messages_python is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# messages_python is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with messages_python.  If not, see <https://www.gnu.org/licenses/>.

import typing
import time
import math
import os,pathlib

import enum

from msgRecord.ivyRecorder import IvyRecorder,MessageLog
from msgRecord.messageLog import NoMessageError


from PyQt5 import QtCore, QtGui
from PyQt5.QtWidgets import QWidget,QApplication,\
                            QSizePolicy,QHeaderView,\
                            QTreeView,QInputDialog

from PyQt5.QtCore import Qt,QSortFilterProxyModel,QModelIndex,pyqtSlot,QTimer
from PyQt5.QtGui import QColor,QStandardItem,QStandardItemModel


class PinnedSenderItem(QStandardItem):
    _COLS = enum.IntEnum('PinnedSenderModel',['Message', 'Field', 'Value', 'Ping'],start=0)
    EXTINCTION_TIME = 5 #seconds
    COLOR_FREQ = True
    
    def __init__(self,sender_id:int):
        super().__init__("")
        self.senderId:int = sender_id
        
    def updateMessages(self,msgs:dict[int,dict[int,MessageLog]]):
        for i in range(self.rowCount()):
            pinItem = self.child(i,0)
            msgItem = self.child(i,len(PinnedMessagesModel._COLS)+self._COLS['Message'])
            fieldItem = self.child(i,len(PinnedMessagesModel._COLS)+self._COLS['Field'])
            valueItem = self.child(i,len(PinnedMessagesModel._COLS)+self._COLS['Value'])
            timeItem = self.child(i,len(PinnedMessagesModel._COLS)+self._COLS['Ping'])
            
            classId = pinItem.data(Qt.ItemDataRole.UserRole)
            msgId = msgItem.data(Qt.ItemDataRole.UserRole)
            fieldName = fieldItem.text()
            
            m = msgs[classId][msgId].newest()
            field = m.get_full_field(fieldName)
            
            valueItem.setData(field.val,Qt.ItemDataRole.UserRole)
            
            if field.format and '%' in field.format:
                valstr = field.format % field.val
            else:
                valstr = str(field.val)
            
            if field.unit and field.unit != 'none':
                valstr += " " + field.unit
            
            if field.is_enum:
                valstr += f" ({field.val_enum})"
            
            valueItem.setText(valstr)
            
            dt = (time.time_ns() - m.timestamp)
            timeItem.setData(dt,Qt.ItemDataRole.UserRole)
            
            dt = dt/10e9 # From ns to s
            timeItem.setText(f" {dt:.0f}s ")
            
            if self.COLOR_FREQ:
                green = int(max(255*(1 - (dt/self.EXTINCTION_TIME)),0))
                        
                back_color = QColor(0,green,0)
                
                srgb = back_color.getRgbF()
                        
                light_remap = lambda v : v/12.92 if v <= 0.03928 else ((v+0.055)/1.055)**2.4
                RGB = tuple(light_remap(v) for v in srgb)
                
                bg_relative_luminance = RGB[0] * 0.2126 + RGB[1] * 0.7152 + RGB[2] * 0.0722
                
                # Original treshold
                # if bg_relative_luminance > math.sqrt(1.05*0.05)-0.05:
                
                # Adjusted for personal preferences
                if bg_relative_luminance > math.sqrt(1.05*0.05)+0.01:
                    front_color = QColor(0,0,0)
                else:
                    front_color = QColor(255,255,255)
                    
                timeItem.setBackground(back_color)
                timeItem.setForeground(front_color)
            
    
            

class PinnedMessagesModel(QStandardItemModel):
    _COLS = enum.IntEnum('MessagesModelHeader',["Sender Id"],start=0)
    
    def __init__(self,ivy_recorder:IvyRecorder, parent: typing.Optional[QtCore.QObject] = None):
        super().__init__(parent)
        
        
        self.setHorizontalHeaderLabels([v.name.replace('_',' ') for v in self._COLS]+[v.name.replace('_',' ') for v in PinnedSenderItem._COLS])
        
        self.ivyRecorder = ivy_recorder        
        self.senderMap:dict[int,int] = dict() # Sender_id -> Row_number
                                
        # self.ivyRecorder.data_updated.connect(self.updateModel)
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.updateTimes)
        
        self.timer.start(200)
        
    
    def mimeTypes(self) -> typing.List[str]:
        return ["text/plain"]
    
    def __mimeStrFromIndex(self,index:QModelIndex) -> typing.Optional[bytes]:
        item = self.itemFromIndex(index)
                
        if isinstance(item,PinnedSenderItem):
            return None
            
        elif isinstance(item.parent(),PinnedSenderItem):
            senderItem:PinnedSenderItem = item.parent()
            
            i = index.row()
            
            pinItem = senderItem.child(i,0)
            msgItem = senderItem.child(i,len(PinnedMessagesModel._COLS)+self._COLS['Message'])
            fieldItem = senderItem.child(i,len(PinnedMessagesModel._COLS)+self._COLS['Field'])
            valueItem = senderItem.child(i,len(PinnedMessagesModel._COLS)+self._COLS['Value'])
            # timeItem = senderItem.child(i,len(PinnedMessagesModel._COLS)+self._COLS['Ping'])
            
            sender = str(senderItem.parent().data(Qt.ItemDataRole.UserRole))
            class_name = pinItem.data(Qt.ItemDataRole.UserRole+1)
            msg_name = msgItem.text()
            
            
            field_name = fieldItem.text()
            field_type = fieldItem.data(Qt.ItemDataRole.UserRole)
            field_scale = fieldItem.data(Qt.ItemDataRole.UserRole+1)
            
            if '[' in field_type:
                array_len = len(valueItem.data(Qt.ItemDataRole.UserRole))
                array_range,ok = QInputDialog.getText(None,
                                                   "Input index or range",
                                                   "Either a number, or a range (both inclusive)",
                                                   text=f"0-{array_len-1}",
                                                   inputMethodHints=Qt.InputMethodHint.ImhFormattedNumbersOnly)
                if not(ok):
                    return None
            else:
                array_range = None
            
            if field_scale is None:
                field_scale = 1.
            
            if array_range is None:
                return f"{sender}:{class_name}:{msg_name}:{field_name}:{field_scale}".encode()
            else:
                return f"{sender}:{class_name}:{msg_name}:{field_name}[{array_range}]:{field_scale}".encode()
        
        else:
            return None
    
    def mimeData(self, indexes: typing.Iterable[QModelIndex]) -> QtCore.QMimeData:
        data = QtCore.QMimeData()
        
        for index in indexes:
            if index.isValid():
                encoded_data = self.__mimeStrFromIndex(index)
                if encoded_data is not None:
                    data.setData("text/plain",encoded_data)
                    break
                
               
        return data
    
    def setData(self, index: QModelIndex, value: typing.Any, role: int = ...) -> bool:
        ret = super().setData(index, value, role)
        
        item = self.itemFromIndex(index)
        if role == Qt.ItemDataRole.CheckStateRole:
            if isinstance(item,PinnedMessageItem):
                item.checkChildren(value)
            elif isinstance(item.parent(),PinnedMessageItem):
                item.parent().setCheckFromChildren()
                
        return ret
    
    def createClassItem(self,class_name:str,class_id:int) -> ClassItem:
        """Create a ClassItem, register it in the model and returns it

        This function will create the corresponding row in the model and update the classMap dictionary.

        Args:
            class_name (str): Name of the new class
            class_id (int): Id of the new class

        Raises:
            ClassItemAlreadyExistsError: If a class with the same Id is already registered, raise this error

        Returns:
            ClassItem: The new ClassItem
        """
        if class_id in self.classMap.keys():
            item:ClassItem = self.item(self.classMap[class_id],0)
            existing_name = item.text()
            
            raise ClassItemAlreadyExistsError(class_id,class_name,existing_name)
        
        
        class_item = ClassItem(class_name)
        class_item.setEditable(False)
        class_row = self.rowCount()
        
        newrow = [class_item]+[QStandardItem() for _ in range(len(ClassItem._COLS))]
        for e in newrow:
            e.setEditable(False)
            e.setDragEnabled(False)
        self.appendRow(newrow)
        
        self.classMap[class_id] = class_row
        return class_item
    
    def pauseUpdates(self,b:bool):
        if b:
            self.timer.stop()
        else:
            self.timer.start()
    
    @pyqtSlot()
    def updateTimes(self):
        for i in range(self.rowCount()):
            senderItem:PinnedSenderItem = self.item(i,0)
            senderItem.updateMessages(self.ivyRecorder.records[senderItem.senderId])

        
    @pyqtSlot(int,int,int,bool)
    def updateModel(self,sender_id:int,class_id:int,msg_id:int,new_msg:bool):        
        if sender_id == self.senderId:
            msg_log = self.ivyRecorder.records[sender_id][class_id][msg_id]
            
            try:
                class_row = self.classMap[class_id]
                class_item:ClassItem = self.item(class_row,0)
            except KeyError:
                class_name = msg_log.msg_class()
                class_item = self.createClassItem(class_name,class_id)
            
            class_item.updateMessage(msg_log)