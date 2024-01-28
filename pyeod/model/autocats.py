import inspect
import re
from functools import wraps
from copy import deepcopy
import math
from .types import Element

user_funcs = {}


def user_func(name=None):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        func_name = name if name else func.__name__
        args = inspect.signature(func).parameters
        if len(args) > 1:
            second_arg_name = list(args.keys())[1]
            second_arg_type = args[second_arg_name].annotation
            user_funcs[func_name] = {
                "type": second_arg_type,
                "func_object": func,
            }
        elif len(args) == 1:
            user_funcs[func_name] = {
                "func_object": func,
            }
        return wrapper

    return decorator


# Used for type hinting args that need to be parsed to be the same type as the current object in the pipe
class CurrentObjectType:
    pass


# Used for type hinting args that need to be parsed to be the same type as the current object's first element in the pipe
class CurrentObjectListSubType:
    pass


re_cache = {}


@user_func()
def regex(current_object, regex_str: str):
    if regex_str not in re_cache:
        re_cache[regex_str] = re.compile(regex_str)
        if len(re_cache) >= 100:
            re_cache.popitem(last=False)
    return bool(re_cache[regex_str].search(current_object))


@user_func(name="=")
def equals(current_object, compare: CurrentObjectType):
    """Checks whether the current is equal to something else\nreturns the same type as the current object"""
    return current_object == compare


@user_func(name=">")
def greater(current_object, number: float):
    """Checks whether the current object is greater than a number\nreturns True or False"""
    return current_object > number


@user_func(name="<")
def lesser(current_object, number: float):
    """Checks whether the current object is less than a number\nreturns True or False"""
    return current_object < number


@user_func(name="floor")
def _floor(current_object):
    """Floors the current object\nreturns the same type as the current object"""
    return float(math.floor(current_object))


@user_func(name="not")
def _not(current_object):
    """Flips the current_object\nreturns True or False"""
    return not current_object


@user_func(name="any")
def _any(current_object):
    """Checks whether any of the objects in the current object exist and are not false\nreturns True or False"""
    return any(current_object)


@user_func(name="all")
def _all(current_object):
    """Checks whether all of the objects in the current object exist and are not False\nreturns True or False"""
    return all(current_object)


@user_func(name="+")
def add(current_object, addition: CurrentObjectType):
    """Adds to the current object\nreturns the same type as the current object"""
    return current_object + addition


@user_func(name="-")
def sub(current_object, subtraction: CurrentObjectType):
    """Subtracts the current object\nreturns the same type as the current object"""
    return current_object - subtraction


@user_func(name="*")
def mult(current_object, multiplication: CurrentObjectType):
    """Multiplies the current object\nreturns the same type as the current object"""
    return current_object * multiplication


@user_func(name="/")
def divide(current_object, division: CurrentObjectType):
    """Divides the current object\nreturns the same type as the current object"""
    return current_object / division


@user_func(name="%")
def modulo(current_object, mod: CurrentObjectType):
    """Modulos the current object\nreturns the same type as the current object"""
    return current_object % mod


@user_func()
def has(current_object, compare: CurrentObjectListSubType):
    """Checks whether the current object has something in it\nreturns True or False"""
    return compare in current_object


@user_func()
def length(current_object):
    """Gets the length of the current object\nreturns a number"""
    return len(current_object)


@user_func()
def get(current_object, index: int):
    """Gets the object of a certain index in the current object\nreturns the same type as the first object in the current object"""
    if index < 0:
        index = len(current_object) + index
    return current_object[index : index + 1]


@user_func()
def sort(current_object):
    """Sorts the current object\nreturns the current object sorted"""
    return sorted(current_object)


@user_func()
def reverse(current_object):
    """Reverses the current object\nreturns the current object reversed"""
    return current_object[::-1]


@user_func()
def exists(current_object):
    """Checks whether the current object exists\nreturns True or False"""
    return bool(current_object)


@user_func(name="->number")
def to_number(current_object):
    """Converts the current object into a number\nreturns a number"""
    return float(current_object)


@user_func(name="->text")
def to_text(current_object):
    """Converts the current object into text\n returns text"""
    return str(current_object)


@user_func()
def _(current_object, echo):
    """Echo function called when using ?(...)\nreturns the parsed innards"""
    return echo


class Token:
    def eat_token(self, token_stack, pointer, token_type):
        if isinstance(token_stack[pointer + 1], token_type):
            return pointer + 1, token_stack[pointer + 1]
        raise Exception("Bad Token")

    def __str__(self):
        return self.__class__.__name__.removesuffix("Token")


class TextToken(Token):
    def __init__(self, text=""):
        self.text = text

    def __str__(self):
        return f'Text<"{self.text}">'


class ItemToken(Token):
    pass


class PropertyGrabToken(Token):
    async def parse(
        self,
        token_stack,
        pointer,
        current_object,
        outer_element_objects,
        element_object,
        server,
    ):
        pointer, prop_to_grab = self.eat_token(token_stack, pointer, TextToken)
        try:
            return pointer, getattr(current_object or element_object, prop_to_grab.text)
        except AttributeError:
            if isinstance(element_object, Element):
                if prop_to_grab.text == "parents":
                    path = await server.db.get_path(element_object)
                    elements = [
                        server.db.elem_id_lookup[x]
                        for x in server.db.min_elem_tree[path[-1]]
                    ]
                    return pointer, elements
            raise


class FunctionCallToken(Token):
    async def parse(
        self,
        token_stack,
        pointer,
        current_object,
        outer_element_objects,
        element_object,
        server,
    ):
        try:
            pointer, function_name = self.eat_token(token_stack, pointer, TextToken)
        except:
            function_name = TextToken("_")  # Shortcut for echo func
        func = user_funcs[function_name.text]
        if "type" in func:
            pointer, _ = self.eat_token(token_stack, pointer, OpenFunctionArgToken)
            shift, untyped_arg = await parse_object(
                deepcopy(current_object),
                token_stack[pointer + 1 :],
                server,
                stop_token=CloseFunctionArgToken,
                outer_element_objects=[element_object] + outer_element_objects,
            )
            if len(current_object) == 0:
                return pointer+shift, False
            try:
                if func["type"] == CurrentObjectType:
                    arg = type(current_object)(untyped_arg)
                elif func["type"] == CurrentObjectListSubType:
                    arg = type(current_object[0])(untyped_arg)
                elif func["type"] == inspect._empty:
                    arg = untyped_arg
                else:
                    arg = func["type"](untyped_arg)

            # Maybe not the best idea?
            except (ValueError, TypeError):
                return pointer + shift, False
            if current_object is None and function_name.text != "_":
                return pointer + shift, False
            return pointer + shift, func["func_object"](current_object, arg)
        else:
            if current_object is None:
                return pointer, False
            func = user_funcs[function_name.text]
            try:
                return pointer, func["func_object"](current_object)
            except (ValueError, TypeError):
                return pointer, False


class OpenFunctionArgToken(Token):
    pass


class CloseFunctionArgToken(Token):
    pass


class BoolOpToken(Token):
    pass


class OrToken(BoolOpToken):
    pass

    def parse(self, left, right):
        return left or right


class AndToken(BoolOpToken):
    pass

    def parse(self, left, right):
        return left and right


class XorToken(BoolOpToken):
    pass

    def parse(self, left, right):
        return left != right


class OpenMappingToken(Token):
    pass


class CloseMappingToken(Token):
    pass


class OpenFilterToken(Token):
    pass


class CloseFilterToken(Token):
    pass


class ScopeOutToken(Token):
    pass


class StopToken(Token):
    pass


token_map = {
    ".": PropertyGrabToken,
    "?": FunctionCallToken,
    "(": OpenFunctionArgToken,
    ")": CloseFunctionArgToken,
    "|": OrToken,
    "&": AndToken,
    "^": XorToken,
    "[": OpenMappingToken,
    "]": CloseMappingToken,
    "{": OpenFilterToken,
    "}": CloseFilterToken,
    "$": ScopeOutToken,
    ";": StopToken,
}


async def tokenize(script: str):
    pattern = re.compile(r"\s+")
    script = re.sub(pattern, "", script)
    token_stack = [TextToken()]
    pointer = 0
    while True:
        current_char = script[pointer : pointer + 1]
        if current_char:
            if current_char in token_map:
                token_stack.append(token_map[current_char]())
            elif current_char == "\\":
                pointer += 1
                current_char = script[pointer : pointer + 1]
                if not isinstance(token_stack[-1], TextToken):
                    token_stack.append(TextToken())
                token_stack[-1].text += current_char
            else:
                if not isinstance(token_stack[-1], TextToken):
                    token_stack.append(TextToken())
                token_stack[-1].text += current_char
        else:
            break
        pointer += 1
    for index, i in enumerate(token_stack):
        if isinstance(i, TextToken) and (
            i.text.lower() == "element" or i.text.lower() == "item"
        ):
            token_stack[index] = ItemToken()
    return token_stack


async def parse_object(
    element_object,
    token_stack: list,
    server,
    *,
    stop_type=type(None),
    stop_token=None,
    outer_element_objects=None,
):
    if not outer_element_objects:
        outer_element_objects = []
    current_object = None
    pointer = 0
    while pointer < len(token_stack) - 1 and (
        stop_type is type(None) or type(current_object) != stop_type
    ):
        token = token_stack[pointer]
        if stop_token and isinstance(token, stop_token):
            token = token_stack[pointer - 1]
            pointer += 1
            break
        outer_shift = -1
        if isinstance(token, ItemToken):
            current_object = element_object
        elif isinstance(token, TextToken):
            pass
        elif isinstance(token, StopToken):
            pass
        elif isinstance(token, ScopeOutToken):
            try:
                while True:
                    pointer, _ = token.eat_token(token_stack, pointer, ScopeOutToken)
                    outer_shift += 1
            except:
                pointer += 1
                token = token_stack[pointer]
                if isinstance(token, ItemToken):
                    current_object = outer_element_objects[outer_shift]
                else:
                    raise Exception('Expected "element" or "item"')
        elif isinstance(token, OpenMappingToken):
            new_list_object = []
            if current_object is False:
                current_object = []
            for item in current_object:
                shift, returned_object = await parse_object(
                    item,
                    token_stack[pointer + 1 :],
                    server,
                    stop_token=CloseMappingToken,
                    outer_element_objects=[element_object] + outer_element_objects,
                )
                new_list_object.append(returned_object)
            if len(current_object) == 0:
                shift = 0
                eat_token = None
                while not isinstance(eat_token, CloseMappingToken):
                    shift += 1
                    eat_token = token_stack[pointer + shift]
            else:
                current_object = new_list_object
            pointer += shift
        elif isinstance(token, OpenFilterToken):
            new_list_object = []
            if current_object is False:
                current_object = []
            for item in current_object:
                shift, returned_object = await parse_object(
                    item,
                    token_stack[pointer + 1 :],
                    server,
                    stop_token=CloseFilterToken,
                    outer_element_objects=[element_object] + outer_element_objects,
                )
                if returned_object:
                    new_list_object.append(item)
            if len(current_object) == 0:
                shift = 0
                eat_token = False
                while not isinstance(eat_token, CloseFilterToken):
                    shift += 1
                    eat_token = token_stack[pointer + shift]
            else:
                current_object = new_list_object
            pointer += shift
        elif isinstance(token, BoolOpToken):
            left = current_object
            shift, right = await parse_object(
                element_object, token_stack[pointer + 1 :], server, stop_type=bool
            )
            current_object = token.parse(left, right)
            pointer += shift
        else:
            pointer, current_object = await token.parse(
                token_stack,
                pointer,
                current_object,
                outer_element_objects,
                element_object,
                server,
            )
        pointer += 1
    if current_object is None:
        if isinstance(token, TextToken):
            current_object = token.text
    if stop_type == type(None) and stop_token is None:
        return current_object
    else:
        return pointer, current_object


def token_list_to_string(token_list, do_spacing=True, do_indents=False):
    out = ""
    if do_indents:
        indentation = 0
    for token in token_list:
        text = next((k for k, v in token_map.items() if v == type(token)), None)
        if text:
            if do_indents:
                if text in r"]}":
                    indentation -= 1
                    out += "\n"
            if text not in r"()[]{}.*" and do_spacing:
                out += " " + text + " "
            elif text in r"([{" and do_spacing:
                out += text + " "
            elif text in r"}])" and do_spacing:
                out += " " + text
            else:
                out += text
            if do_indents:
                if text in r"[{":
                    indentation += 1
                    out += "\n" + "  " * indentation
        elif isinstance(token, TextToken):
            out += token.text
        elif isinstance(token, ItemToken):
            out += "Element"
    return out


# Tests
if __name__ == "__main__":
    script = r"""

    """

    class Element:
        def __init__(self, name: str, id: int, parents=[]):
            self.id = id
            self.name = name
            self.parents = parents

        def __str__(self):
            return f"Element:{self.name} \nId:{self.id}"

    e0 = Element("void", 1)
    e1 = Element("fire", 2, [e0])
    e2 = Element("water", 3, [e0])
    e3 = Element("1", 4, [e1, e2])

    tokens = tokenize(script)

    print("\n-   Input Script:")
    print(script)
    print("\n-   Input:")
    print(e3)
    print("\n-   Tokenized Form:")
    for i in tokens:
        print(i)
    # result = await parse_object(e3, tokens)
    print("\n-   Result:")
    # print(result)

    print("\n\n\n")
    print(token_list_to_string(tokens, False))
