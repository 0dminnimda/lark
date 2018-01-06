"""This module implements a LALR(1) Parser
"""
# Author: Erez Shinan (2017)
# Email : erezshin@gmail.com

from ..common import ParseError, UnexpectedToken

from .lalr_analysis import LALR_Analyzer, Shift

class FinalReduce:
    def __init__(self, value):
        self.value = value

class Parser:
    def __init__(self, parser_conf):
        assert all(o is None or o.priority is None for n,x,a,o in parser_conf.rules), "LALR doesn't yet support prioritization"
        self.analysis = analysis = LALR_Analyzer(parser_conf.rules, parser_conf.start)
        analysis.compute_lookahead()
        callbacks = {rule: getattr(parser_conf.callback, rule.alias or rule.origin, None)
                          for rule in analysis.rules}

        self.parser = _Parser(analysis.parse_table, callbacks)
        self.parse = self.parser.parse

class _Parser:
    def __init__(self, parse_table, callbacks):
        self.states = parse_table.states
        self.start_state = parse_table.start_state
        self.end_state = parse_table.end_state
        self.callbacks = callbacks

    def parse(self, seq, set_state=None):
        i = 0
        token = None
        stream = iter(seq)
        states = self.states

        state_stack = [self.start_state]
        value_stack = []

        if set_state: set_state(self.start_state)

        def get_action(key):
            state = state_stack[-1]
            try:
                return states[state][key]
            except KeyError:
                expected = states[state].keys()

                raise UnexpectedToken(token, expected, seq, i)

        def reduce(rule):
            size = len(rule.expansion)
            if size:
                s = value_stack[-size:]
                del state_stack[-size:]
                del value_stack[-size:]
            else:
                s = []

            value = self.callbacks[rule](s)

            _action, new_state = get_action(rule.origin)
            assert _action is Shift
            state_stack.append(new_state)
            value_stack.append(value)

        # Main LALR-parser loop
        try:
            token = next(stream)
            i += 1
            while True:
                action, arg = get_action(token.type)
                assert arg != self.end_state

                if action is Shift:
                    state_stack.append(arg)
                    value_stack.append(token)
                    if set_state: set_state(arg)
                    token = next(stream)
                    i += 1
                else:
                    reduce(arg)
        except StopIteration:
            pass

        while True:
            _action, arg = get_action('$end')
            if _action is Shift:
                assert arg == self.end_state
                val ,= value_stack
                return val
            else:
                reduce(arg)
