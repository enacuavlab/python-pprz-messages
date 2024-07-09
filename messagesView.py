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

from PyQt5.QtCore import Qt,QSortFilterProxyModel,QModelIndex,QTimer,pyqtSlot,pyqtSignal
from PyQt5.QtGui import QColor,QStandardItem,QStandardItemModel




class MessageItem(QStandardItem):
    _COLS = enum.IntEnum('MessageItemHeader',['Field_name', 'Value', 'Alt_value'],start=0)
    
    def __init__(self,name:str):
        super().__init__("")
        self.fieldsMap:dict[str,int] = dict() # Field_name -> Row_number
        self.msgName:str = name
            
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
    
    def updateFields(self,msg:MessageLog):
        m = msg.newest()
        fields = m.msg._fields.values()
        
        for f in fields:
            try:
                rowNum = self.fieldsMap[f.name]
                valueItem = self.child(rowNum,len(MessagesModel._COLS) + self._COLS["Value"])
                altvalueItem = self.child(rowNum,len(MessagesModel._COLS) + self._COLS["Alt_value"])
            except KeyError:
                fieldnameItem = QStandardItem(f"({f.typestr}) {f.name}")
                fieldnameItem.setData(f.name,Qt.ItemDataRole.UserRole)
                fieldnameItem.setData(f.typestr,Qt.ItemDataRole.UserRole+1)
                valueItem = QStandardItem()
                altvalueItem = QStandardItem()
                pinItem = QStandardItem()
                pinItem.setCheckable(True)
                # pinItem.setIcon(self.model().pinIcon)
                
                fieldnameItem.setEditable(False)
                valueItem.setEditable(False)
                altvalueItem.setEditable(False)
                
                newitems = [None] * len(self._COLS)
                newitems[self._COLS['Field_name']] = fieldnameItem
                newitems[self._COLS['Value']] = valueItem
                newitems[self._COLS['Alt_value']] = altvalueItem
                
                self.fieldsMap[f.name] = self.rowCount()
                
                newrow = [pinItem] + newitems
                for e in newrow:
                    e.setEditable(False)
                self.appendRow(newrow)

            
            
            # valueItem.setData(f.val,Qt.ItemDataRole.DisplayRole)
            valueItem.setData(f.val,Qt.ItemDataRole.UserRole)
            
            if f.format and '%' in f.format:
                valstr = f.format % f.val
            else:
                valstr = str(f.val)
            
            if f.unit and f.unit != 'none':
                valstr += " " + f.unit
            
            if f.is_enum:
                valstr += f" ({f.val_enum})"
            
            valueItem.setText(valstr)
                        
            if f.val is not None and not(f.array_type):
                alt_coef = 1. if f.alt_unit_coef is None else f.alt_unit_coef
                
                # altvalueItem.setData(alt_coef * f.val,Qt.ItemDataRole.DisplayRole)
                altvalueItem.setData(alt_coef * f.val,Qt.ItemDataRole.UserRole)
                altvalueItem.setData(alt_coef,Qt.ItemDataRole.UserRole+1)
                
                if f.alt_unit_coef != 1. and f.alt_unit_coef != None:
                    altstr = f"{f.val * f.alt_unit_coef:.3f}"
                    
                    if f.alt_unit:
                        altstr += " " + f.alt_unit
                        
                    altvalueItem.setText(altstr)

class ClassItemAlreadyExistsError(Exception):
    def __init__(self, class_id:int,class_name:str,existing_name:str) -> None:
        msg = f"Tried to re-create an exiting class with Id {class_id}\n(New name '{class_name}' VS Existing '{existing_name}')"
        super().__init__(msg) 

class ClassItem(QStandardItem):
    _COLS = enum.IntEnum('ClassItemHeader',['Name','Id',"Reception"],start=0)
    EXTINCTION_TIME = 5 #seconds
    COLOR_FREQ = True
    
    def __init__(self,name:str):
        super().__init__(name)
        self.messagesMap:dict[int,int] = dict() # Msg_id -> Row_number
        
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
            rowNum = self.messagesMap[id]
            msgItem = self.child(rowNum, 0)
            
            timeItem = self.child(rowNum,len(MessagesModel._COLS)+self._COLS['Reception'])
            timeItem.setData(dt,Qt.ItemDataRole.UserRole)
            timeItem.setText(f" {dt:.0f}s ({freq:.1f} Hz) ")
            
        except KeyError:
            self.messagesMap[id] = self.rowCount()
            
            msgItem = MessageItem(name)
            msgItem.setCheckable(True)
            msgItem.setAutoTristate(True)
            msgItem.setCheckState(Qt.CheckState.Unchecked)
            # msgItem.setIcon(self.model().pinIcon)            
            
            idItem = QStandardItem(str(id))
            idItem.setData(id,Qt.ItemDataRole.DisplayRole)
            idItem.setData(id,Qt.ItemDataRole.UserRole)
            
            nameItem = QStandardItem(name)
            nameItem.setData(name,Qt.ItemDataRole.UserRole)
            
            timeItem = QStandardItem(f" {dt:.0f}s ({freq:.1f} Hz) ")
            timeItem.setData(dt,Qt.ItemDataRole.UserRole)
            
            idItem.setEditable(False)
            nameItem.setEditable(False)
            timeItem.setEditable(False)
            
            newitems = [None] * len(self._COLS)
            newitems[self._COLS['Id']] = idItem
            newitems[self._COLS['Name']] = nameItem
            newitems[self._COLS['Reception']] = timeItem
            
            newrow = [msgItem] + newitems
            for e in newrow:
                e.setEditable(False)
            self.appendRow(newrow)
            
            print(f"Added row for {name}")


                
        msgItem.updateFields(msg)
        
        intfreq = int(freq*10)
        if intfreq >= 100:
            intfreq = round(intfreq/100)*100
        
        timeItem.setData(intfreq,Qt.ItemDataRole.UserRole)
        
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
        
        

class MessagesModel(QStandardItemModel):
    _COLS = enum.IntEnum('MessagesModelHeader',["Class"],start=0)
    newPin = pyqtSignal(int,int,int,str,bool)
    
    def __init__(self,ivy_recorder:IvyRecorder, sender_id:int,parent: typing.Optional[QtCore.QObject] = None):
        super().__init__(parent)
        
        
        self.setHorizontalHeaderLabels([v.name.replace('_',' ') for v in self._COLS]+[v.name.replace('_',' ')+' / '+w.name.replace('_',' ') for v,w in zip(ClassItem._COLS,MessageItem._COLS)])
        
        self.ivyRecorder = ivy_recorder
        self.senderId = sender_id
        
        self.classMap:dict[int,int] = dict() # Class_id -> Row_number
                                
        # self.ivyRecorder.data_updated.connect(self.updateModel)
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.updateTimes)
        
        self.timer.start(500)
        
    
    def mimeTypes(self) -> typing.List[str]:
        return ["text/plain"]
    
    def __mimeStrFromIndex(self,index:QModelIndex) -> typing.Optional[bytes]:
        item = self.itemFromIndex(index)
                
        if isinstance(item,MessageItem):
            classItem:ClassItem = item.parent()
            
            sender = str(self.senderId)
            class_name = classItem.text()
            msg_name = item.msgName
            
            return f"{sender}:{class_name}:{msg_name}".encode()
            
        elif isinstance(item.parent(),MessageItem):
            msgItem:MessageItem = item.parent()
            classItem:ClassItem = msgItem.parent()
            
            sender = str(self.senderId)
            class_name = classItem.text()
            msg_name = msgItem.msgName
            
            field_name = msgItem.child(index.row(),len(self._COLS)+MessageItem._COLS['Field_name']).data(Qt.ItemDataRole.UserRole)
            field_type = msgItem.child(index.row(),len(self._COLS)+MessageItem._COLS['Field_name']).data(Qt.ItemDataRole.UserRole+1)

            field_scale = msgItem.child(index.row(),len(self._COLS)+MessageItem._COLS['Alt_value']).data(Qt.ItemDataRole.UserRole+1)
            
            if '[' in field_type:
                array_len = len(msgItem.child(index.row(),len(self._COLS)+MessageItem._COLS['Value']).data(Qt.ItemDataRole.UserRole))
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
            if isinstance(item,MessageItem):
                item.checkChildren(value)
            elif isinstance(item.parent(),MessageItem):
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
        try:
            classes = self.ivyRecorder.records[self.senderId]
        except KeyError:
            return
        
        
        for class_id,msgs in classes.items():
            try:
                class_item:ClassItem = self.item(self.classMap[class_id],0)
            except KeyError:
                if len(msgs) == 0:
                    print("No messages ?")
                    continue

                class_name = next(iter(msgs.values())).msg_class()
                    
                class_item = self.createClassItem(class_name,class_id)
            
            for m in msgs.values():
                class_item.updateMessage(m)

        
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
            
        
class MessagesFilteredModel(QSortFilterProxyModel):
    def __init__(self, parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)
        
        self.__checkedOnly = False
    
    def messageCount(self) -> int:
        self.blockSignals(True)
        total = 0
        classCount = self.rowCount()
        for i in range(classCount):
            total += self.rowCount(self.index(i,0))
        self.blockSignals(False)
        return total
    
    def setCheckedOnly(self,b:bool):
        self.__checkedOnly = b
        self.invalidateFilter()
                
    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        firstIndex = source_parent.child(source_row,0)
        model:MessagesModel = self.sourceModel()
        item:QStandardItem = model.itemFromIndex(firstIndex)
        
        if self.__checkedOnly:
            try:
                checkstatus = item.checkState() != Qt.CheckState.Unchecked
            except AttributeError:
                checkstatus = True
        else:
            checkstatus = True
        
        regex = self.filterRegularExpression()
        
        if len(regex.pattern()) == 0:
            regex_result = True
        elif isinstance(item,ClassItem):
            regex_result = True
        elif isinstance(item,MessageItem):
            msgNameItem:QStandardItem = model.itemFromIndex(source_parent.child(source_row,len(MessagesModel._COLS)+ClassItem._COLS['Name']))
            msgIdItem:QStandardItem = model.itemFromIndex(source_parent.child(source_row,len(MessagesModel._COLS)+ClassItem._COLS['Id']))
            
            regex_result = regex.match(msgNameItem.text()).hasMatch() or regex.match(msgIdItem.text()).hasMatch()
            
            if not(regex_result):
                # Child rows results:
                for i in range(item.rowCount()):
                    if self.filterAcceptsRow(i,item.index()):
                        regex_result = True
                        break
            
        else:
            try:
                fieldNameItem:QStandardItem = model.itemFromIndex(source_parent.child(source_row,len(MessagesModel._COLS) + MessageItem._COLS['Field_name']))
                regex_result = regex.match(fieldNameItem.text()).hasMatch()
                
                
                if not (regex_result):
                    msgNameItem:QStandardItem = model.itemFromIndex(source_parent.parent().child(source_parent.row(),len(MessagesModel._COLS)+ClassItem._COLS['Name']))
                    msgIdItem:QStandardItem = model.itemFromIndex(source_parent.parent().child(source_parent.row(),len(MessagesModel._COLS)+ClassItem._COLS['Id']))
            
                    regex_result = regex.match(msgNameItem.text()).hasMatch() or regex.match(msgIdItem.text()).hasMatch()
            
            except AttributeError:
                regex_result = True

        return checkstatus and regex_result

class MessagesView(QTreeView):
    def __init__(self, ivy:IvyRecorder,sender_id:int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        
        self.ivy_recorder:IvyRecorder = ivy
        self.senderId = sender_id
        self.backModel = MessagesModel(ivy,sender_id,self)
        self.proxyModel = MessagesFilteredModel(self)

        self.proxyModel.setSourceModel(self.backModel)
        self.proxyModel.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.proxyModel.setSortRole(Qt.ItemDataRole.UserRole)

        self.setModel(self.proxyModel)
        
        self.setSortingEnabled(True)
        self.sortByColumn(0,Qt.SortOrder.AscendingOrder)
        
        self.setSizeAdjustPolicy(QTreeView.SizeAdjustPolicy.AdjustToContents)
        self.sizePolicy().setHorizontalPolicy(QSizePolicy.Policy.Minimum)
        self.sizePolicy().setVerticalPolicy(QSizePolicy.Policy.Minimum)
        self.header().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        
        self.setWordWrap(False)
        
        self.doubleClicked.connect(self.__expandAllOnDoubleClick)
        self.model().rowsInserted.connect(self.__autoExpandTopItems)
        
        self.setSelectionBehavior(QTreeView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QTreeView.SelectionMode.SingleSelection)
        self.setDragDropMode(self.DragDropMode.DragOnly)
                
        self.ivy_recorder.recordSender(sender_id)
        
        localdir =  pathlib.Path(__file__).parent
        
        style = """
QTreeView::indicator:unchecked{
    image: url(:/icons/pin/normal/16.png);
}

QTreeView::indicator:checked{
    image: url(:/icons/pin/active_straight/16.png);
}

QTreeView::indicator:indeterminate{
    image: url(:/icons/pin/active/16.png);
}

/* 
QTreeView::branch:has-siblings:!adjoins-item {
    border-image: url(:/images/vline.png) 0;
}
*/

QTreeView::branch:has-siblings:adjoins-item {
    border-image: url(:/images/branch-more.png) 0;
}

QTreeView::branch:!has-children:!has-siblings:adjoins-item {
    border-image: url(:/images/branch-end.png) 0;
}

QTreeView::branch:has-children:!has-siblings:closed,
QTreeView::branch:closed:has-children:has-siblings {
        border-image: none;
        image: url(:/images/branch-closed.png);
}

QTreeView::branch:open:has-children:!has-siblings,
QTreeView::branch:open:has-children:has-siblings  {
        border-image: none;
        image: url(:/images/branch-open.png);
}
                            """.replace('url(:',f'url({localdir}')
                        
        self.setStyleSheet(style)
          
    @pyqtSlot(QModelIndex)
    def __expandAllOnDoubleClick(self,index:QModelIndex):
        rootIndex = index.parent().child(index.row(),0)
        if self.isExpanded(rootIndex):
            self.collapse(rootIndex)
        else:
            self.expand(rootIndex)
            
    @pyqtSlot(QModelIndex,int,int)
    def __autoExpandTopItems(self,parent:QModelIndex,start:int,stop:int):
        if not(parent.isValid()):
            return
        
        if not(parent.parent().isValid()):
            if not(self.isExpanded(parent)):
                self.expand(parent)
    
    @pyqtSlot()
    def safeExpandAll(self):
        if self.model().messageCount() < 5:
            self.expandAll()
        
            
            
        
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser("Debug MessagesView")
    parser.add_argument('sender_id',type=int,help="ID of the sender to record")
    
    args = parser.parse_args()
    
    app = QApplication([])
    
    ivy = IvyRecorder()
    sender_id = args.sender_id
    
    while not sender_id in ivy.known_senders.keys():
        try:
            print(f"Waiting for Id {sender_id}")
            time.sleep(0.1)
        except KeyboardInterrupt:
            ivy.stop()
            exit(0)
            
    window = MessagesView(ivy,sender_id,None)
    
    app.aboutToQuit.connect(ivy.stop)
    
    window.show()
    app.exec()