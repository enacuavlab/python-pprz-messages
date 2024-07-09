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
from functools import total_ordering


from collections import deque

from pprzlink.message import PprzMessage,PprzMessageField

@total_ordering
class TimedPprzMessage():
    def __init__(self, msg:PprzMessage, t:typing.Optional[int]=None):
        self.msg = msg
        self._timestamp = time.time_ns() if t is None else t
    
    def get_full_field(self, fieldname:str) -> PprzMessageField:
        return self.msg.get_full_field(fieldname)
    
    @property
    def name(self) -> str:
        return self.msg.name
    
    @property
    def msg_class(self) -> str:
        return self.msg.msg_class
    
    @property
    def msg_id(self) -> int:
        return self.msg.msg_id
    
    @property
    def class_id(self) -> int:
        return self.msg.class_id
        
    @property
    def timestamp(self) -> int:
        """Get the message reception timestamp."""
        return self._timestamp
    
    # @property.setter
    # def timestamp(self,t:int) -> int:
    #     """Set the message reception timestamp."""
    #     self._timestamp = t
        
    def timeit(self) -> int:
        """ Set the timestamp to NOW (in ns, since Epoch), and returns it"""
        self._timestamp = time.time_ns()
        return self._timestamp
    
    def __eq__(self,other)->bool:
        return self._timestamp == other._timestamp and self.name == other.name
    
    def __lt__(self,other)->bool:
        return self.timestamp < other.timestamp
        

class NoMessageError(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__("No messages in this log")

class MessageLog():
    def __init__(self,size:int=10):
        self.queue:typing.Deque[TimedPprzMessage] = deque(maxlen=size)
        self.period:typing.Optional[float] = None 
        
    def addMessage(self,msg:TimedPprzMessage):
        if len(self.queue) > 0:
            if self.period is None:
                self.period = msg.timestamp - self.queue[0].timestamp
            else:
                self.period = (msg.timestamp - self.queue[0].timestamp + self.period)/2
        
        self.queue.appendleft(msg)
        
    def addMessages(self,msgs:typing.Iterable[TimedPprzMessage]):
        sorted_msgs = sorted(msgs)
        if self.period is None:
            self.period = (sorted_msgs[-1] - sorted_msgs[0])/len(sorted_msgs)
        else:
            self.period = ((sorted_msgs[-1] - sorted_msgs[0])/len(sorted_msgs) + self.period)/2
        self.queue.extendleft(sorted_msgs)
    
    def newest(self) -> TimedPprzMessage:
        try:
            return self.queue[0]
        except IndexError:
            raise NoMessageError()
    
    def meanFreq(self) -> float:
        if self.period is None:
            raise NoMessageError()
        else:
            return 10e9/self.period #ns to s, then s to Hz
    
    def msg_name(self) -> str:
        return self.newest().name
    
    def msg_class(self) -> str:
        return self.newest().msg_class
    
    def msg_id(self) -> int:
        return self.newest().msg_id
    
    def class_id(self) -> int:
        return self.newest().class_id
    
    def sample_count(self) -> int:
        return len(self.queue)
    
    def get_full_field(self, fieldname:str) -> PprzMessageField:
        return self.newest().get_full_field(fieldname)
    

    
    
    
            
    