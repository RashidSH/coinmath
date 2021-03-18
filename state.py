# -*- coding: utf-8 -*-

class State:
    def __init__(self, default_state):
        self.default_state = default_state

        self.state = {}
        self.examples_state = {}

    def get(self, user_id):
        if user_id not in self.state:
            return self.default_state

        return self.state[user_id]

    def set(self, user_id, new_state):
        self.state[user_id] = new_state

    def get_example(self, user_id):
        return self.examples_state[user_id]

    def set_example(self, user_id, level, example, answer):
        self.set(user_id, 'example')

        self.examples_state[user_id] = {
            'level': level,
            'example': example,
            'answer': answer,
        }
