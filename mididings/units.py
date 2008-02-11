# -*- coding: utf-8 -*-
#
# mididings
#
# Copyright (C) 2008  Dominic Sacré  <dominic.sacre@gmx.de>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#

import _mididings
import main as _main
import util as _util
from event import *


class _Unit:
    def __rshift__(self, other):
        return _Chain(self, other)

    def __rrshift__(self, other):
        return _Chain(other, self)


class _Chain(_Unit):
    def __init__(self, first, second):
        self.items = first, second


class Fork(list, _Unit):
    def __init__(self, l):
        list.__init__(self, l)


class TypeFork(Fork):
    def __init__(self, t, l):
        a = [ (TypeFilter(t) >> x) for x in l ] + \
            [ ~TypeFilter(t) ]
        list.__init__(self, a)

def NoteFork(x):
    return TypeFork(TYPE_NOTE, x)

def CtrlFork(x):
    return TypeFork(TYPE_CTRL, x)

def PitchbendFork(x):
    return TypeFork(TYPE_PITCHBEND, x)

def ProgFork(x):
    return TypeFork(TYPE_PROGRAM, x)


def Divide(t, x, y):
    return Fork([ TypeFilter(t) >> x, ~TypeFilter(t) >> y ])

def NoteDivide(x, y):
    return Divide(TYPE_NOTE, x, y)

def CtrlDivide(x, y):
    return Divide(TYPE_CTRL, x, y)

def PitchbendDivide(x, y):
    return Divide(TYPE_PITCHBEND, x, y)

def ProgDivide(x, y):
    return Divide(TYPE_PROGRAM, x, y)


# base class for all filters, supporting operator ~
class _Filter(_Unit):
    def __invert__(self):
        return _InvertedFilter(self)

class _Modifier(_Unit):
    pass


class _InvertedFilter(_mididings.InvertedFilter, _Unit):
    pass


class Pass(_mididings.Pass, _Unit):
    def __init__(self, p=True):
        _mididings.Pass.__init__(self, p)

def Discard():
    return Pass(False)


### filters ###

class TypeFilter(_mididings.TypeFilter, _Filter):
    def __init__(self, type_):
        _mididings.TypeFilter.__init__(self, type_)

def NoteGate():
    return TypeFilter(TYPE_NOTE)

def CtrlGate():
    return TypeFilter(TYPE_CTRL)

def PitchbendGate():
    return TypeFilter(TYPE_PITCHBEND)

def ProgGate():
    return TypeFilter(TYPE_PROGRAM)


class PortFilter(_mididings.PortFilter, _Filter):
    def __init__(self, *args):
        vec = _mididings.int_vector()
        for port in _util.flatten(args):
            vec.push_back(port - _main.DATA_OFFSET)
        _mididings.PortFilter.__init__(self, vec)


class ChannelFilter(_mididings.ChannelFilter, _Filter):
    def __init__(self, *args):
        vec = _mididings.int_vector()
        for c in _util.flatten(args):
            vec.push_back(c - _main.DATA_OFFSET)
        _mididings.ChannelFilter.__init__(self, vec)


class KeyFilter(_mididings.KeyFilter, _Filter):
    def __init__(self, *args):
        if len(args) == 1:
            args = args[0]
        r = _util.noterange2numbers(args)
        _mididings.KeyFilter.__init__(self, r[0], r[1])


class VeloFilter(_mididings.VeloFilter, _Filter):
    def __init__(self, *args):
        if len(args) == 1:
            args = args[0]
        _mididings.VeloFilter.__init__(self, args[0], args[1])


class CtrlFilter(_mididings.CtrlFilter, _Filter):
    def __init__(self, controller):
        _mididings.CtrlFilter.__init__(self, controller)


### splits ###

def PortSplit(d):
    return Fork([ (PortFilter(p) >> w) for p, w in d.items() ])

def ChannelSplit(d):
    return Fork([ (ChannelFilter(c) >> w) for c, w in d.items() ])


def KeySplit(*args):
    if len(args) == 1:
        # KeySplit(d)
        return NoteFork([ (KeyFilter(k) >> w) for k, w in args[0].items() ])
    elif len(args) == 3:
        # KeySplit(key, units_lower, units_upper)
        key, units_lower, units_upper = args
        filt = KeyFilter(0, key)
        return NoteFork([ filt >> units_lower, ~filt >> units_upper ])
    else:
        raise ArgumentError()


def VeloSplit(*args):
    if len(args) == 1:
        # VelocitySplit(d)
        return NoteFork([ (VeloFilter(v) >> w) for v, w in args[0].items() ])
    elif len(args) == 3:
        # VelocitySplit(thresh, units_lower, units_upper)
        thresh, units_lower, units_upper = args
        filt = VeloFilter(0, thresh)
        return NoteFork([ filt >> units_lower, ~filt >> units_upper ])
    else:
        raise ArgumentError()


### modifiers ###

class Port(_mididings.Port, _Modifier):
    def __init__(self, port):
        _mididings.Port.__init__(self, port - _main.DATA_OFFSET)


class Channel(_mididings.Channel, _Modifier):
    def __init__(self, channel):
        _mididings.Channel.__init__(self, channel - _main.DATA_OFFSET)


class Transpose(_mididings.Transpose, _Modifier):
    def __init__(self, offset):
        _mididings.Transpose.__init__(self, offset)


class Velocity(_mididings.Velocity, _Modifier):
    OFFSET = 1
    MULTIPLY = 2
    FIXED = 3
    def __init__(self, value, mode=OFFSET):
        _mididings.Velocity.__init__(self, value, mode)

def VelocityOffset(value):
    return Velocity(value, Velocity.OFFSET)

def VelocityMultiply(value):
    return Velocity(value, Velocity.MULTIPLY)

def VelocityFixed(value):
    return Velocity(value, Velocity.FIXED)


class VeloGradient(_mididings.VeloGradient, _Modifier):
    def __init__(self, note_lower, note_upper, value_lower, value_upper, mode=Velocity.OFFSET):
        _mididings.VeloGradient.__init__(self,
            _util.note2number(note_lower), _util.note2number(note_upper),
            value_lower, value_upper, mode)

def VeloGradientOffset(note_lower, note_upper, value_lower, value_upper):
    return VeloGradient(note_lower, note_upper, value_lower, value_upper, Velocity.OFFSET)

def VeloGradientMultiply(note_lower, note_upper, value_lower, value_upper):
    return VeloGradient(note_lower, note_upper, value_lower, value_upper, Velocity.MULTIPLY)

def VeloGradientFixed(note_lower, note_upper, value_lower, value_upper):
    return VeloGradient(note_lower, note_upper, value_lower, value_upper, Velocity.FIXED)


class CtrlRange(_mididings.CtrlRange, _Modifier):
    def __init__(self, controller, in_min, in_max, out_min, out_max):
        _mididings.CtrlRange.__init__(self, controller, in_min, in_max, out_min, out_max)


### misc ###

class GenerateEvent(_mididings.GenerateEvent, _Unit):
    def __init__(self, type_, port, channel, data1, data2):
        _mididings.GenerateEvent.__init__(self, type_,
                port - _main.DATA_OFFSET if port >= 0 else port,
                channel - _main.DATA_OFFSET if channel >= 0 else channel,
                data1, data2)


def CtrlChange(*args):
    if len(args) == 2:
        # ControlChange(controller, value)
        controller, value = args
        return GenerateEvent(TYPE_CTRL, _main.DATA_OFFSET,
                             _main.DATA_OFFSET, controller, value)
    elif len(args) == 4:
        # ControlChange(port, channel, controller, value)
        port, channel, controller, value = args
        return GenerateEvent(TYPE_CTRL, port, channel, controller, value)
    else:
        raise ArgumentError()


def ProgChange(*args):
    if len(args) == 1:
        # ProgramChange(program)
        return GenerateEvent(TYPE_PROGRAM, _main.DATA_OFFSET,
                             _main.DATA_OFFSET, 0, args[0] - _main.DATA_OFFSET)
    elif len(args) == 3:
        # ProgramChange(port, channel, program)
        port, channel, program = args
        return GenerateEvent(TYPE_PROGRAM, port, channel, 0, program - _main.DATA_OFFSET)
    else:
        raise ArgumentError()


class PatchSwitch(_mididings.PatchSwitch, _Unit):
    def __init__(self, num=PROGRAM):
        _mididings.PatchSwitch.__init__(self, num)


class Call(_mididings.Call, _Unit):
    def __init__(self, fun):
        self.fun = fun
        _mididings.Call.__init__(self, self.do_call)
    def do_call(self, ev):
        # foist a few more properties
        ev.__class__ = MidiEvent
        return self.fun(ev)

#class CallAsync(_mididings.Call, _Unit):
#    def __init__(self, fun):
#        self.fun = fun
#        _mididings.Call.__init__(self, self.do_call_async)
#    def do_call_async(self, ev):
#        ev.__class__ = _MidiEvent
#        Q.put((self.fun, ev))
#        return False


class Print(Call):
    def __init__(self, name=None):
        self.name = name
        Call.__init__(self, self.do_print)

    def do_print(self, ev):
        if self.name:
            print self.name + ":",

        if ev.type_ == TYPE_NOTEON:
            t = "note on"
            d1 = "note " + str(ev.note) + " (" + _util.notenumber2name(ev.note) + ")"
            d2 = "velocity " + str(ev.velocity)
        elif ev.type_ == TYPE_NOTEOFF:
            t = "note off"
            d1 = "note " + str(ev.note) + " (" + _util.notenumber2name(ev.note) + ")"
            d2 = "velocity " + str(ev.velocity)
        elif ev.type_ == TYPE_CTRL:
            t = "control change"
            d1 = "param " + str(ev.param)
            d2 = "value " + str(ev.value)
        elif ev.type_ == TYPE_PITCHBEND:
            t = "pitch bend"
            d1 = None
            d2 = "value " + str(ev.value)
        elif ev.type_ == TYPE_PROGRAM:
            t = "program change"
            d1 = None
            d2 = "program " + str(ev.program)
        else:
            t = "none"
            d1 = None
            d2 = "-"

        print "%s: port %d, channel %d," % (t, ev.port, ev.channel),
        if d1 != None:
            print "%s," % (d1,),
        print "%s" % (d2,)
