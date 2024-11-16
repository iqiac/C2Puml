import re
from abc import ABC, abstractmethod
from typing import Optional


class ParserLeaf(ABC):
    _leaf_map = {
        re.compile(r'^Utility_Link\w+\('): 'UtilityLeaf',
        re.compile(r'\b\w+Graph_Create\('): 'ExternalGraphLeaf',
    }

    def __init__(self, call, scope) -> None:
        self._call = call
        self._scope = scope

    @abstractmethod
    def translate(self) -> list:
        pass

    def _add_scope(self, s):
        if '.' in s:  # Scope already present
            return s
        if not self._scope:  # No scope given
            return s
        return self._scope + '.' + s

    @classmethod
    def create(cls, call, scope) -> Optional['ParserLeaf']:
        # Factory-like method to decide which subclass to instantiate
        for pattern, leaf_class in cls._leaf_map.items():
            if pattern.search(call):
                # Dynamically instantiate correct subclass
                return globals()[leaf_class](call, scope)
        return None


class UtilityLeaf(ParserLeaf):
    def translate(self) -> list:
        match [s.strip() for s in re.split('[(),]', self._call) if s]:
            case ['Utility_LinkDirectedHard', parent, child]:
                parent, child = self._add_scope(parent), self._add_scope(child)
                return [f'({parent}) --> ({child})']
            case ['Utility_LinkDirectedSoft', parent, child]:
                parent, child = self._add_scope(parent), self._add_scope(child)
                return [f'({parent}) ..> ({child})']
            case ['Utility_LinkUndirected', parent, child]:
                parent, child = self._add_scope(parent), self._add_scope(child)
                return [f'({parent}) -- ({child})']
            case _:
                print(
                    f'{self.__class__.__name__}: "{self._call}" does not fit any regex.'
                )
                return []


class ExternalGraphLeaf(ParserLeaf):
    def translate(self) -> list:
        match [s.strip() for s in re.split('[_( ]', self._call) if s]:
            case ['Graph', varname, '=', gname, 'Create', *_]:
                return [
                    f'cloud "{gname}" as {varname} {{',
                    f'  ({varname}.start) . ({varname}.end)',
                    '}',
                ]
            case _:
                print(
                    f'{self.__class__.__name__}: "{self._call}" does not fit any regex.'
                )
                return []
