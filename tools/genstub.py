#!/usr/bin/env python3
import argparse
from pathlib import Path
import jinja2
import json
import re
import os

TEMPLATE = """\
//
//  DO NOT MODIFY: Message definitions for {{ name }} interface generated by genstub.py.
//
#![allow(unused)]
#![allow(clippy::unused_unit)]
#![allow(clippy::let_and_return)]

use crate::prelude::*;
use crate::arch::syscall;
use crate::page::PageBase;
use crate::thread_info::set_page_base;

{% macro define_message(msg, reply) %}
{% set fields = msg.rets if reply else msg.args %}
pub const {{ msg.name | upper }}{{ "_REPLY" if reply }}_MSG_INLINE_LEN: usize
    = ({{ fields | inline_len }});
pub const {{ msg.name | upper }}{{ "_REPLY" if reply }}_MSG: MessageHeader =
    MessageHeader::new( \
        (((INTERFACE_ID as u32) << 8) \
        {{ "| MSG_REPLY_FLAG" if reply }} \
        | {{ msg.attrs.id }}) << MSG_TYPE_OFFSET \
{%- if fields.page -%}
        | MSG_PAGE_PAYLOAD \
{%- endif -%}
{%- if fields.channel -%}
        | MSG_CHANNEL_PAYLOAD \
{%- endif -%}
        | (({{ msg.name | upper }}{{ "_REPLY" if reply }}_MSG_INLINE_LEN as u32)
            << MSG_INLINE_LEN_OFFSET) \
    );

#[repr(C, packed)]
pub struct {{ msg.name | camelcase }}{{ "Reply" if reply }}Msg {
    pub header: MessageHeader,
    pub from: CId,
    pub notification: Notification,
{%- if fields.channel %}
    pub {{ fields.channel.name }}: CId,
{%- else %}
    __unused_channel: CId,
{%- endif %}
{%- if fields.page %}
    pub {{ fields.page.name }}: RawPage,
{%- else %}
    __unused_page: RawPage,
{%- endif %}
{%- for field in fields.inlines %}
    pub {{ field.name }}: {{ field.type | resolve_type_in_msg_struct }},
{%- endfor %}
    __unused_data: [u8;
        INLINE_PAYLOAD_LEN_MAX -
            {{ msg.name | upper }}{{ "_REPLY" if reply }}_MSG_INLINE_LEN]
}
{% endmacro %}

{% macro serialize(var, name, fields, reply) %}
    {{ var }}.header = {{ name | upper }}{{ "_REPLY" if reply }}_MSG;
{%- if fields.page %}
    {{ var }}.{{ fields.page.name }} = {{ fields.page.name }}.as_raw_page();
{%- endif %}
{%- if fields.channel %}
    {{ var }}.{{ fields.channel.name }} = {{ fields.channel.name }}.cid();
{%- endif %}
{%- for field in fields.inlines %}
    {{ var }}.{{ field.name }} = {{ field | to_payload }};
{%- endfor %}
{% endmacro %}

{% macro deserialize(var, name, fields) %}
{%- if fields.fields | length == 1 %}
    {{ fields.fields[0] | from_payload(var + ".") }}
{%- else %}
    (
    {%- for field in fields.fields -%}
        {{ field | from_payload(var + ".") }},
    {%- endfor -%}
    )
{%- endif %}
{% endmacro %}

pub const INTERFACE_ID: u8 = {{ attrs.id }};

#[inline]
fn __cast_from_message<T>(m: &Message) -> &T {
    unsafe { &*(m as *const Message as *const T) }
}

#[inline]
fn __cast_from_message_mut<T>(m: &mut Message) -> &mut T {
    unsafe { &mut *(m as *mut Message as *mut T) }
}

#[inline]
fn __cast_into_message<T>(m: &T) -> &Message {
    unsafe { &*(m as *const T as *const Message) }
}

//
//  Message definitions.
//
{% for msg in messages %}
{{ define_message(msg, False) }}
{%- if msg.attrs.type == "call" %}
{{ define_message(msg, True) }}
{%- endif %}
{%- endfor %}

//
//  Send stubs.
//
{% for msg in messages %}
pub fn send_{{ msg.name }}({{ msg.args | arg_params("__ch: &Channel") }})
    -> Result<()> {
    let mut __m: {{ msg.name | camelcase }}Msg =
        unsafe { core::mem::MaybeUninit::uninit().assume_init() };
    {{ serialize("__m", msg.name, msg.args, False) }}
    __ch.send(__cast_into_message(&__m))
}
pub fn nbsend_{{ msg.name }}({{ msg.args | arg_params("__ch: &Channel") }})
    -> Result<()> {
    let mut __m: {{ msg.name | camelcase }}Msg =
        unsafe { core::mem::MaybeUninit::uninit().assume_init() };
    {{ serialize("__m", msg.name, msg.args, False) }}
    __ch.send_noblock(__cast_into_message(&__m))
}

{%- if msg.attrs.type == "call" %}
pub fn call_{{ msg.name }}({{ msg.args | arg_params("__ch: &Channel") }}) -> Result<{{ msg.rets | ret_params }}> {
    let mut __m: {{ msg.name | camelcase }}Msg =
        unsafe { core::mem::MaybeUninit::uninit().assume_init() };
{%- if msg.rets.page %}
    set_page_base(PageBase::allocate());
{%- endif %}
    {{ serialize("__m", msg.name, msg.args, False) }}
    __ch.call(__cast_into_message(&__m))
        .map(|__r| {
            let __r: &{{ msg.name | camelcase }}ReplyMsg = __cast_from_message(&__r);
            {{ deserialize("__r", msg.name, msg.rets) }}
        })
}

pub fn send_{{ msg.name }}_reply({{ msg.rets | arg_params("__ch: &Channel") }})
    -> Result<()> {
    let mut __m: {{ msg.name | camelcase }}ReplyMsg =
        unsafe { core::mem::MaybeUninit::uninit().assume_init() };
    {{ serialize("__m", msg.name, msg.rets, True) }}
    __ch.send(__cast_into_message(&__m))
}

pub fn nbsend_{{ msg.name }}_reply({{ msg.rets | arg_params("__ch: &Channel") }})
    -> Result<()> {
    let mut __m: {{ msg.name | camelcase }}ReplyMsg =
        unsafe { core::mem::MaybeUninit::uninit().assume_init() };
    {{ serialize("__m", msg.name, msg.rets, True) }}
    __ch.send_noblock(__cast_into_message(&__m))
}
{%- endif %}
{% endfor -%}

//
//  Server stubs.
//
pub trait Server {
{%- for msg in messages %}
{%- if msg.attrs.type == "call" %}
    fn {{ msg.name }}({{ msg.args | arg_params("&mut self, _from: &Channel") }})
        -> Result<{{ msg.rets | ret_params }}>;
{%- endif %}
{%- if msg.attrs.type == "oneway" %}
    fn {{ msg.name }}({{ msg.args | arg_params("&mut self, _from: &Channel") }});
{%- endif %}
{%- endfor %}

    fn __handle(&mut self, m: &mut Message) -> bool {
        match m.header {
{%- for msg in messages %}
{%- if msg.attrs.type == "call" %}
            {{ msg.name | upper }}_MSG => {
                let req: &mut {{ msg.name | camelcase }}Msg =
                    __cast_from_message_mut(m);
                let from = Channel::from_cid(req.from);
                match self.{{ msg.name }}({{ msg.args | call_args("req") }}) {
                    Ok(rets) => {
                        let __resp: &mut {{ msg.name | camelcase }}ReplyMsg
                            = __cast_from_message_mut(m);
                        {%- if msg.rets.fields | length == 1 %}
                            let {{ msg.rets.fields[0].name }} = rets;
                        {%- else %}
                            {%- for field in msg.rets.fields %}
                                let {{ field.name }} = rets.{{ loop.index0 }};
                            {%- endfor %}
                        {%- endif %}
                        {{ serialize("__resp", msg.name, msg.rets, True) }}
                        true
                    }
                    Err(Error::NoReply) => {
                        false
                    }
                    Err(err) => {
                        m.header = MessageHeader::from_error(err);
                        true
                    }
                }
            }
{%- elif msg.attrs.type == "oneway" %}
            {{ msg.name | upper }}_MSG => {
                let req: &mut {{ msg.name | camelcase }}Msg =
                    __cast_from_message_mut(m);
                let from = Channel::from_cid(req.from);
                self.{{ msg.name }}({{ msg.args | call_args("req") }});
                false
            }
{%- endif %}
{%- endfor %}
            _ => {
                m.header = MessageHeader::from_error(Error::UnknownMessage);
                true
            },
        }
    }
}

pub trait Client {
{%- for msg in messages %}
{%- if msg.attrs.type == "call" %}
    fn {{ msg.name }}_reply({{ msg.rets | arg_params("&mut self, _from: &Channel") }}) {}
{%- endif %}
{%- endfor %}

    fn __handle(&mut self, m: &mut Message) -> bool {
        match m.header {
{%- for msg in messages %}
{%- if msg.attrs.type == "call" %}
            {{ msg.name | upper }}_REPLY_MSG => {
                let reply: &mut {{ msg.name | camelcase }}ReplyMsg =
                    __cast_from_message_mut(m);
                let from = Channel::from_cid(reply.from);
                self.{{ msg.name }}_reply({{ msg.rets | call_args("reply") }});
                false
            }
{%- endif %}
{%- endfor %}
            _ => {
                m.header = MessageHeader::from_error(Error::UnknownMessage);
                true
            },
        }
    }
}
"""

builtin_types = {
    "int8":     { "type_in_msg": None,          "name": "i8",       "size": "core::mem::size_of::<i8>()" },
    "int16":    { "type_in_msg": None,          "name": "i16",      "size": "core::mem::size_of::<i16>()" },
    "int32":    { "type_in_msg": None,          "name": "i32",      "size": "core::mem::size_of::<i32>()" },
    "int64":    { "type_in_msg": None,          "name": "i64",      "size": "core::mem::size_of::<i64>()" },
    "uint8":    { "type_in_msg": None,          "name": "u8",       "size": "core::mem::size_of::<u8>()" },
    "uint16":   { "type_in_msg": None,          "name": "u16",      "size": "core::mem::size_of::<u16>()" },
    "uint32":   { "type_in_msg": None,          "name": "u32",      "size": "core::mem::size_of::<u32>()" },
    "uint64":   { "type_in_msg": None,          "name": "u64",      "size": "core::mem::size_of::<u64>()" },
    "bool":     { "type_in_msg": None,          "name": "bool",     "size": "core::mem::size_of::<bool>()" },
    "char":     { "type_in_msg": None,          "name": "u8",       "size": "core::mem::size_of::<u8>()" },
    "handle":   { "type_in_msg": None,          "name": "HandleId", "size": "core::mem::size_of::<HandleId>()" },
    "channel":  { "type_in_msg": None,          "name": "Channel",  "size": "0" },
    "page":     { "type_in_msg": None,          "name": "Page",     "size": "0" },
    "intmax":   { "type_in_msg": None,          "name": "isize",    "size": "core::mem::size_of::<isize>()" },
    "uintmax":  { "type_in_msg": None,          "name": "usize",    "size": "core::mem::size_of::<usize>()" },
    "uintptr":  { "type_in_msg": None,          "name": "usize",    "size": "core::mem::size_of::<usize>()" },
    "paddr":    { "type_in_msg": None,          "name": "usize",    "size": "core::mem::size_of::<usize>()" },
    "size":     { "type_in_msg": None,          "name": "usize",    "size": "core::mem::size_of::<usize>()" },
    "string":   { "type_in_msg": "FixedString", "name": "&str",     "size": "core::mem::size_of::<FixedString>()" },
}

# Resolves a type name to a corresponding builtin type.
def resolve_type(type_name):
    assert type_name in builtin_types
    return builtin_types[type_name]["name"]

def resolve_type_in_arg(type_name):
    assert type_name in builtin_types
    if builtin_types[type_name]["type_in_arg"] is not None:
        return builtin_types[type_name]["type_in_arg"]
    else:
        return builtin_types[type_name]["name"]

def resolve_type_in_msg_struct(type_name):
    assert type_name in builtin_types
    if builtin_types[type_name]["type_in_msg"] is not None:
        return builtin_types[type_name]["type_in_msg"]
    else:
        return builtin_types[type_name]["name"]

def inline_len(params):
    sizes = []
    for field in params["inlines"]:
        typename = field["type"]
        sizes.append(builtin_types[typename]["size"])
    if len(sizes) == 0:
        return "0"
    else:
        return " + ".join(sizes)

def call_args(args, msg_var):
    values = ["&from"]
    for arg in args["fields"]:
        value = f"{msg_var}.{arg['name']}"
        if arg["type"] == "channel":
            values.append(f"Channel::from_cid({value})")
        elif arg["type"] == "page":
            values.append(f"{value}.into_page(set_page_base(PageBase::allocate()))")
        elif arg["type"] in ["string"]:
            values.append(f"{value}.to_str()")
        else:
            values.append(f"{value}")
    return ", ".join(values)

def arg_params(args, first_param):
    params = [first_param]
    for arg in args["fields"]:
        params.append(f"{arg['name']}: {resolve_type(arg['type'])}")
    return ", ".join(params)

def ret_params(rets):
    params = []
    for ret in rets["fields"]:
        if ret["type"] == "string":
            params.append("String")
        else:
            params.append(resolve_type(ret['type']))
    if len(params) == 1:
        return params[0]
    else:
        return "(" + ", ".join(params) + ")"

def from_payload(field, prefix=None):
    if prefix:
        expr = prefix + field["name"]
    else:
        expr = field["name"]

    if field["type"] == "string":
        return f"{expr}.to_string()"
    elif field["type"] == "page":
        return f"{expr}.into_page(set_page_base(PageBase::allocate()))"
    elif field["type"] == "channel":
        return f"Channel::from_cid({expr})"
    else:
        return f"{expr}"

def to_payload(field):
    if field["type"] == "string":
        return f"FixedString::from_str(&{field['name']})"
    elif field["type"] == "channel":
        return f"{field['name']}.cid()"
    else:
        return f"{field['name']}"

def genstub(out_dir, idl):
    renderer = jinja2.Environment()
    renderer.filters["camelcase"] \
        = lambda x: "".join(map(lambda frag: frag.title(), x.split("_")))
    renderer.filters["resolve_type"] = resolve_type
    renderer.filters["resolve_type_in_msg_struct"] = resolve_type_in_msg_struct
    renderer.filters["inline_len"] = inline_len
    renderer.filters["arg_params"] = arg_params
    renderer.filters["ret_params"] = ret_params
    renderer.filters["call_args"] = call_args
    renderer.filters["to_payload"] = to_payload
    renderer.filters["from_payload"] = from_payload

    os.makedirs(out_dir, exist_ok=True)
    with open(Path(out_dir) / "README.md", "w") as f:
        f.write("# IDL stubs files generated by genstub.py")

    with open(Path(out_dir) / "mod.rs", "w") as mod:
        for interface in idl:
            stub = renderer.from_string(TEMPLATE).render(**interface)
            with open(Path(out_dir) / (interface["name"] + ".rs"), "w") as f:
                f.write(stub)

            mod.write(f"pub mod {interface['name']};\n")

def main():
    parser = argparse.ArgumentParser(description="The IDL stub generator.")
    parser.add_argument("idl_json", help="The parsed IDL JSON file.")
    parser.add_argument("out_dir", help="The output diretory.")
    args = parser.parse_args()

    idl = json.load(open(args.idl_json))
    genstub(args.out_dir, idl)

if __name__ == "__main__":
    main()
