# Copyright (C) 2024 Mael FEURGARD <mael.feurgard@enac.fr>
# 
# This file is part of python-pprz-messages.
# 
# python-pprz-messages is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# python-pprz-messages is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with python-pprz-messages.  If not, see <https://www.gnu.org/licenses/>.

import typing
import time
import math
import os,pathlib

import enum

from msgRecord.ivyRecorder import IvyRecorder,MessageLog
from msgRecord.messageLog import NoMessageError

from PyQt5 import QtCore
from PyQt5.QtWidgets import QInputDialog
from PyQt5.QtCore import Qt,QObject,QSortFilterProxyModel,QModelIndex,QTimer,pyqtSlot,pyqtSignal
from PyQt5.QtGui import QColor,QStandardItem,QStandardItemModel

#################### Columns mapping ####################

COLUMN_COUNT = 3


class FieldColumns(enum.IntEnum):
        ROOT = 0
        VALUE = 1
        ALT_VALUE = 2

assert len(FieldColumns) <= COLUMN_COUNT


class MessageColumns(enum.IntEnum):
        ROOT = 0
        ID = 1
        RECEPTION = 2

assert len(MessageColumns) <= COLUMN_COUNT


class MessageClassColumns(enum.IntEnum):
        ROOT = 0
        
assert len(MessageClassColumns) <= COLUMN_COUNT


class SenderColumns(enum.IntEnum):
        ROOT = 0
        
assert len(SenderColumns) <= COLUMN_COUNT

#################### Specific items ####################

class FieldItem(QStandardItem):
    def __init__(self,name:str):
        super().__init__(name)
        self.setFieldName(name)
        
    def getSenderId(self) -> int:
        return self.parent().getSenderId()
        
    def setFieldName(self,name:str):
        self.setData(name,Qt.ItemDataRole.UserRole)
    
    def getFieldName(self) -> str:
        return self.data(Qt.ItemDataRole.UserRole)

class MessageItem(QStandardItem):
    def __init__(self,msg:MessageLog):
        super().__init__(msg.msg_name())
        self.fieldMap:dict[str,int] = dict() # Field_name -> Row_number
        self.msg = msg
        
    def getSenderId(self) -> int:
        return self.parent().getSenderId()
    
    def setCheckFromChildren(self):
        resultState = self.child(0,0).checkState()
        
        for i in range(1,self.rowCount()):
            pinItem = self.child(i,0)
            s = pinItem.checkState()
            if s != resultState:
                self.setCheckState(Qt.CheckState.PartiallyChecked)
                return
        
        self.setCheckState(resultState)
    
    def checkChildren(self,checked:typing.Optional[typing.Union[bool,Qt.CheckState]]=None):
        if checked is None:
            checked = self.checkState()
            
        if checked == Qt.CheckState.PartiallyChecked:
            return
            
        if isinstance(checked,bool):
            checked = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
            
            
        for i in range(self.rowCount()):
            pinItem = self.child(i,0)
            pinItem.setCheckState(checked)
        
    def updateAllFields(self,msg:MessageLog):
        self.msg = msg
        for f in msg.fieldnames():
            self.updateField(msg,f)
    
    def updateField(self,msg:MessageLog,fieldname:str):
        self.msg = msg
        field = msg.get_full_field(fieldname)
        
        try:
            rowNumber = self.fieldMap[fieldname]
            
            fieldRootItem:FieldItem = self.child(rowNumber,FieldColumns.ROOT)
            fieldValueItem = self.child(rowNumber,FieldColumns.VALUE)
            fieldAltValItem = self.child(rowNumber,FieldColumns.ALT_VALUE)
        except KeyError:
            self.fieldMap[fieldname] = self.rowCount()
    
            fieldRootItem = FieldItem(field.name)
            fieldRootItem.setText(f"({field.typestr}) {field.name}")
            fieldRootItem.setCheckable(True)
            fieldRootItem.setEditable(False)
            fieldRootItem.setData(field.name,Qt.ItemDataRole.UserRole)
            
            fieldValueItem = QStandardItem()
            fieldValueItem.setEditable(False)
            
            fieldAltValItem = QStandardItem()
            fieldAltValItem.setEditable(False)
            
            newitems = [None] * COLUMN_COUNT
            newitems[FieldColumns.ROOT] = fieldRootItem
            newitems[FieldColumns.VALUE] = fieldValueItem
            newitems[FieldColumns.ALT_VALUE] = fieldAltValItem
            
            self.appendRow(newitems)
            
        
        fieldValueItem.setData(field.val,Qt.ItemDataRole.UserRole)
            
        if field.format and '%' in field.format:
            valstr = field.format % field.val
        else:
            valstr = str(field.val)
        
        if field.unit and field.unit != 'none':
            valstr += " " + field.unit
        
        if field.is_enum:
            valstr += f" ({field.val_enum})"
        
        fieldValueItem.setText(valstr)
                    
        if field.val is not None and not(field.array_type):
            alt_coef = 1. if field.alt_unit_coef is None else field.alt_unit_coef
            
            fieldAltValItem.setData(alt_coef * field.val,Qt.ItemDataRole.UserRole)
            fieldAltValItem.setData(alt_coef,Qt.ItemDataRole.UserRole+1)
            
            if field.alt_unit_coef != 1. and field.alt_unit_coef != None:
                altstr = f"{field.val * field.alt_unit_coef:.3f}"
                
                if field.alt_unit:
                    altstr += " " + field.alt_unit
                    
                fieldAltValItem.setText(altstr)
            

class MessageClassItem(QStandardItem):
    COLOR_FREQ = True
    EXTINCTION_TIME = 5 # Time before total fade to black of freq coloring, in seconds
    
    def __init__(self,name:str):
        super().__init__(name)
        self.messagesMap:dict[int,int] = dict() # Message_id -> Row_number
        
    def getSenderId(self) -> int:
        return self.parent().getSenderId()
        
    def updateMessage(self,msg:MessageLog):
        id = msg.msg_id()
        name = msg.msg_name()
        timestamp = msg.newest().timestamp
        dt = (time.time_ns() - timestamp)/10e9
        
        try:
            freq = msg.meanFreq()
        except NoMessageError:
            freq = 0
        
        try:
            rowNumber = self.messagesMap[id]
            
            msgRootItem:MessageItem = self.child(rowNumber, MessageColumns.ROOT)
            msgReceptionItem = self.child(rowNumber,MessageColumns.RECEPTION)
            
            
        except KeyError:
            self.messagesMap[id] = self.rowCount()
            
            msgRootItem = MessageItem(msg)
            msgRootItem.setEditable(False)
            msgRootItem.setCheckable(True)
            msgRootItem.setAutoTristate(True)
            msgRootItem.setCheckState(Qt.CheckState.Unchecked)
            # msgItem.setIcon(self.model().pinIcon)            
            
            msgIdItem = QStandardItem(str(id))
            msgIdItem.setData(id,Qt.ItemDataRole.DisplayRole)
            msgIdItem.setData(id,Qt.ItemDataRole.UserRole)
            msgIdItem.setEditable(False)
            
            msgReceptionItem = QStandardItem()
            msgReceptionItem.setEditable(False)
            
            newitems = [None] * COLUMN_COUNT
            newitems[MessageColumns.ROOT] = msgRootItem
            newitems[MessageColumns.ID] = msgIdItem
            newitems[MessageColumns.RECEPTION] = msgReceptionItem
            
            self.appendRow(newitems)
            
            print(f"Added row for {name}")

        msgReceptionItem.setData(dt,Qt.ItemDataRole.UserRole)
        msgReceptionItem.setText(f" {dt:.0f}s ({freq:.1f} Hz) ")
                
        msgRootItem.updateAllFields(msg)
        
        intfreq = int(freq*10)
        if intfreq >= 100:
            intfreq = round(intfreq/100)*100
        
        msgReceptionItem.setData(intfreq,Qt.ItemDataRole.UserRole)
        
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
                
            msgReceptionItem.setBackground(back_color)
            msgReceptionItem.setForeground(front_color)
        

class SenderItem(QStandardItem):
    def __init__(self,senderId:int):
        super().__init__(str(senderId))
        self.setSenderId(senderId)
        self.classMap:dict[int,int] = dict() # Class_id -> Row_number
        
    def setSenderId(self,id:int):
        self.setData(id,Qt.ItemDataRole.UserRole)
        
    def getSenderId(self) -> int:
        return self.data(Qt.ItemDataRole.UserRole)
        
    def updateMessage(self,msg:MessageLog):
        class_name = msg.msg_class()
        class_id = msg.class_id()
        
        try:
            rowNumber = self.classMap[class_id]
            
            clsRootItem = self.child(rowNumber,MessageClassColumns.ROOT)
        except KeyError:
            self.classMap[class_id] = self.rowCount()
            
            clsRootItem = MessageClassItem(class_name)
            clsRootItem.setData(class_name,Qt.ItemDataRole.UserRole)
            
            newItems = [QStandardItem() for i in range(COLUMN_COUNT)]
            newItems[MessageClassColumns.ROOT] = clsRootItem
            
            for i in newItems:
                i.setEditable(False)
            
            self.appendRow(newItems)
            
        clsRootItem.updateMessage(msg)
        
        
    def updateMessageClass(self,ivy:IvyRecorder,class_id:int):
        senderId = self.getSenderId()
        try:
            msgDict = ivy.records[senderId][class_id]
        except KeyError:
            return
        
        for msg in msgDict.values():
            self.updateMessage(msg)
            

#################### Model ####################

class IvyModel(QStandardItemModel):
    _COLS = enum.IntEnum('MessagesModelHeader',["Class"],start=0)
    newPin = pyqtSignal(int,int,int,str,bool)
    
    def __init__(self,ivy_recorder:IvyRecorder, parent: typing.Optional[QObject] = None):
        super().__init__(parent)
        
        
        self.setHorizontalHeaderLabels(["Name","Id/Value","Time/Alt Value"])
        
        self.ivyRecorder = ivy_recorder
        
        self.senderMap:dict[int,int] = dict() # Sender_id -> Row_number
              
        # self.ivyRecorder.data_updated.connect(self.updateModel)
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.updateTimes)
        
        self.timer.start(500)
        
    
    ############### MIME aspects (Drag N Drop) ###############
    
    def mimeTypes(self) -> typing.List[str]:
        return ["text/plain"]
    
    def __mimeStrFromIndex(self,index:QModelIndex) -> typing.Optional[bytes]:
        item = self.itemFromIndex(index)
        parent = item.parent()
        rootItem = parent.child(item.row(),0)
        
        if isinstance(rootItem,MessageClassItem) or isinstance(rootItem,SenderItem):
            return None
        
        elif isinstance(rootItem,MessageItem):
            sender = rootItem.getSenderId()
            class_name = rootItem.msg.msg_class()
            msg_name = rootItem.msg.msg_name()
            
            return f"{sender}:{class_name}:{msg_name}".encode()
            
        elif isinstance(rootItem,FieldItem):
            parent:MessageItem
            
            sender = parent.getSenderId()
            class_name = parent.msg.msg_class()
            msg_name = parent.msg.msg_name()
            field_name = rootItem.getFieldName()
            
            field = parent.msg.get_full_field(field_name)
            field_type = field.typestr
            field_scale = field.alt_unit_coef
            
            if '[' in field_type:
                array_len = len(field.val)
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
        parent = item.parent()
        if role == Qt.ItemDataRole.CheckStateRole:
            if isinstance(item,MessageItem):
                item.checkChildren(value)
            elif isinstance(parent,MessageItem):
                parent.setCheckFromChildren()
                
                
        return ret
    
    
    def pauseUpdates(self,b:bool):
        if b:
            self.timer.stop()
        else:
            self.timer.start()
    
    ############### Updating the model ###############
    
    @pyqtSlot()
    def updateTimes(self):
        for senderId in self.ivyRecorder.records.keys():
            try:
                rowNumber = self.senderMap[senderId]
                
                senderItem:SenderItem = self.item(rowNumber,0)
            except KeyError:
                self.senderMap[senderId] = self.rowCount() 
                
                senderItem = SenderItem(senderId)
                
                newItems = [QStandardItem()] * COLUMN_COUNT
                newItems[SenderColumns.ROOT] = senderItem
                
                for i in newItems:
                    i.setEditable(False)
                
                self.appendRow(newItems)
                
                
            for clsId in self.ivyRecorder.records[senderId].keys():
                senderItem.updateMessageClass(self.ivyRecorder,clsId)
            


class FilteredIvyModel(QSortFilterProxyModel):
    def __init__(self, ivyModel:IvyModel, parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)
        
        self.setSourceModel(ivyModel)
        self.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.setSortRole(Qt.ItemDataRole.UserRole)
        
        self.__checkedOnly = False
    
    def getSenderIndex(self,senderId:int) -> QModelIndex:
        ivyModel:IvyModel = self.sourceModel()
        ivyIndex = ivyModel.index(ivyModel.senderMap[senderId],0)
        return self.mapFromSource(ivyIndex)
    
    def messageCount(self,senderId:int) -> int:
        self.blockSignals(True)
        total = 0
        srcModel:IvyModel = self.sourceModel()
        srcSenderIndex = srcModel.index(srcModel.senderMap[senderId],0)
        senderIndex = self.mapFromSource(srcSenderIndex)
        
        
        classCount = self.rowCount(senderIndex)
        for i in range(classCount):
            total += self.rowCount(self.index(i,0,senderIndex))
        self.blockSignals(False)
        return total
    
    def setCheckedOnly(self,b:bool):
        self.__checkedOnly = b
        self.invalidateFilter()
                
    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        firstIndex = source_parent.child(source_row,0)
        model:IvyModel = self.sourceModel()
        item = model.itemFromIndex(firstIndex)
        
        if self.__checkedOnly:
            if isinstance(item,MessageItem) or isinstance(item,FieldItem):
                try:
                    checkstatus = item.checkState() != Qt.CheckState.Unchecked
                except AttributeError:
                    checkstatus = True
            else:
                checkstatus = True
        else:
            checkstatus = True
        
        regex = self.filterRegularExpression()
        
        if len(regex.pattern()) == 0:
            regex_result = True
        elif isinstance(item,MessageItem):
            msgName = item.msg.msg_name()
            msgId = item.msg.msg_id()
            
            regex_result = regex.match(msgName).hasMatch() or regex.match(str(msgId)).hasMatch()
            
            if not(regex_result):
                # Child rows results:
                for i in range(item.rowCount()):
                    if self.filterAcceptsRow(i,item.index()):
                        regex_result = True
                        break
            
        elif isinstance(item,FieldItem):
            fieldName = item.getFieldName()
            regex_result = regex.match(fieldName).hasMatch()
            
            
            if not (regex_result):
                msgItem:MessageItem = item.parent()
                msgName = msgItem.msg.msg_name()
                msgId = msgItem.msg.msg_id()
        
                regex_result = regex.match(msgName).hasMatch() or regex.match(str(msgId)).hasMatch()
            
        else:
            regex_result = True

        return checkstatus and regex_result