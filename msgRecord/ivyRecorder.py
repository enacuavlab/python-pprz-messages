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

from pprzlink.ivy import IvyMessagesInterface
from pprzlink.message import PprzMessage

from msgRecord.messageLog import MessageLog,TimedPprzMessage

from PyQt5.QtCore import QObject,pyqtSignal

class UnknownSenderError(Exception):
    def __init__(self, sender_id:int,known_ids:list[int]) -> None:
        super().__init__(f"Cannot record unknown sender: {sender_id}\nKnown senders are: {known_ids}")

class IvyRecorder(QObject):
    data_updated = pyqtSignal(int,int,int,bool) # (sender_id,class_id,msg_id,new_msg)
    new_sender = pyqtSignal(int) # (sender_id)
    
    def __init__(self,name:str="IvyRecorder",ivy_bus:typing.Optional[str]=None,buffer_size:int=10) -> None:
        super().__init__()
        
        self.ivy = IvyMessagesInterface(name,ivy_bus=ivy_bus) if ivy_bus is not None else IvyMessagesInterface(name)
        
        # Size of buffers for MessageLog
        self.buffer_size = buffer_size
        
        # Mapping from sender_id to bind_id (or None if the sender is known but has no binds)
        self.known_senders:dict[int,typing.Optional[int]] = dict()
        
        # Mapping : sender_id -> class_id -> message_id -> MessageLog
        self.records:dict[int,dict[int,dict[int,MessageLog]]] = dict()
        
        
        # Subscribe to everything for detecting senders
        self.ivy.subscribe(self.__detectSenders)
        
        # Start Ivy
        self.ivy.start()
        
    def __detectSenders(self,sender_id:int,msg:PprzMessage):
        sender_id = int(sender_id)
        if not(sender_id in self.known_senders.keys()):
            self.known_senders[sender_id] = None
            self.records[sender_id] = dict()
            self.new_sender.emit(sender_id)
        
    def __recordMessage(self,sender_id:int,msg:PprzMessage):
        sender_id = int(sender_id)
        timed_msg = TimedPprzMessage(msg)
        new_msg = False
        
        try:
            class_dict = self.records[sender_id][timed_msg.class_id]
        except KeyError:
            self.records[sender_id][timed_msg.class_id] = dict()
            class_dict = self.records[sender_id][timed_msg.class_id]
        
        try:
            self.records[sender_id][timed_msg.class_id][timed_msg.msg_id].addMessage(timed_msg)
        except KeyError:
            self.records[sender_id][timed_msg.class_id][timed_msg.msg_id] = MessageLog(self.buffer_size)
            self.records[sender_id][timed_msg.class_id][timed_msg.msg_id].addMessage(timed_msg)
            new_msg = True
            
        self.data_updated.emit(sender_id,timed_msg.class_id,timed_msg.msg_id,new_msg)
        

    def recordSender(self,sender_id:int):
        try:
            bind = self.known_senders[sender_id]
        except KeyError:
            raise UnknownSenderError(sender_id,list(self.known_senders.keys()))
        
        if bind is None:
            # print(f"Binding to {sender_id}")
            if int(sender_id) == 0:
                bind_id = self.ivy.subscribe(self.__recordMessage,f'^([a-zA-Z]+ .*)')
            else:                
                bind_id = self.ivy.subscribe(self.__recordMessage,f'^({sender_id} .*)')
            self.known_senders[sender_id] = bind_id
            
    def stopRecordingSender(self,sender_id:int):
        try:
            bind = self.known_senders[sender_id]
        except KeyError:
            raise UnknownSenderError(sender_id,list(self.known_senders.keys()))
        
        if bind is not None:
            self.ivy.unsubscribe(bind)
            self.known_senders[sender_id] = None
            
    def stop(self):
        self.ivy.stop()
        
        