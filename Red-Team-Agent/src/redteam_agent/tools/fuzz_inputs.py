"""fuzz_inputs MCP tool — generate intelligent fuzzing inputs for testing."""

from __future__ import annotations

import json
from typing import Any

from claude_agent_sdk import tool

from redteam_agent.analyzers.payload_generator import get_fuzz_inputs, Payload
from redteam_agent.state import add_payload_result


@tool(
    "fuzz_inputs",
    "Generate intelligent fuzzing inputs: boundary values, format strings, encoding "
    "tricks, special characters, overflow attempts, and protocol-specific payloads. "
    "Optional: 'input_type' (string, number, json, url, email, filename) to get "
    "type-specific fuzz inputs.",
    {"input_type": str},
)
async def fuzz_inputs(args: dict[str, Any]) -> dict[str, Any]:
    input_type = args.get("input_type", "all")

    # Base fuzz inputs
    payloads = get_fuzz_inputs()

    # Add type-specific payloads
    if input_type == "number":
        payloads.extend(_number_fuzz())
    elif input_type == "string":
        payloads.extend(_string_fuzz())
    elif input_type == "json":
        payloads.extend(_json_fuzz())
    elif input_type == "url":
        payloads.extend(_url_fuzz())
    elif input_type == "email":
        payloads.extend(_email_fuzz())
    elif input_type == "filename":
        payloads.extend(_filename_fuzz())

    add_payload_result({
        "tool": "fuzz_inputs",
        "input_type": input_type,
        "payloads_generated": len(payloads),
    })

    result = {
        "input_type": input_type,
        "total_inputs": len(payloads),
        "inputs": [p.to_dict() for p in payloads],
        "usage": "Feed these inputs into your application's input handlers and monitor for crashes, errors, or unexpected behavior.",
    }

    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}


def _number_fuzz() -> list[Payload]:
    return [
        Payload("fuzz_number", "zero", "0", "Zero value", "low"),
        Payload("fuzz_number", "negative_one", "-1", "Negative one", "low"),
        Payload("fuzz_number", "max_int32", "2147483647", "Max 32-bit signed integer", "medium"),
        Payload("fuzz_number", "min_int32", "-2147483648", "Min 32-bit signed integer", "medium"),
        Payload("fuzz_number", "max_int64", "9223372036854775807", "Max 64-bit signed integer", "medium"),
        Payload("fuzz_number", "overflow_int32", "2147483648", "Int32 overflow (max+1)", "medium"),
        Payload("fuzz_number", "float_precision", "0.1 + 0.2", "Floating point precision", "low"),
        Payload("fuzz_number", "scientific", "1e308", "Very large scientific notation", "medium"),
        Payload("fuzz_number", "negative_zero", "-0", "Negative zero", "low"),
        Payload("fuzz_number", "hex_number", "0xDEADBEEF", "Hex notation", "low"),
    ]


def _string_fuzz() -> list[Payload]:
    return [
        Payload("fuzz_string", "single_char", "a", "Single character", "low"),
        Payload("fuzz_string", "unicode_emoji", "\U0001f4a9\U0001f525\U0001f680", "Emoji characters", "low"),
        Payload("fuzz_string", "unicode_math", "\u222b\u2211\u221e\u00b1", "Math symbols", "low"),
        Payload("fuzz_string", "cjk_chars", "\u4e2d\u6587\u65e5\u672c\u8a9e", "CJK characters", "low"),
        Payload("fuzz_string", "null_in_string", "hello\x00world", "Null byte in middle", "medium"),
        Payload("fuzz_string", "tabs_newlines", "line1\t\tline2\n\nline3\r\n", "Mixed whitespace", "low"),
        Payload("fuzz_string", "backslash_heavy", "\\\\\\\\\\\\\\\\", "Many backslashes", "low"),
        Payload("fuzz_string", "quotes_mixed", """he said "it's" fine""", "Mixed quotes", "low"),
    ]


def _json_fuzz() -> list[Payload]:
    return [
        Payload("fuzz_json", "empty_object", "{}", "Empty JSON object", "low"),
        Payload("fuzz_json", "empty_array", "[]", "Empty JSON array", "low"),
        Payload("fuzz_json", "null_value", '{"key": null}', "Null value", "low"),
        Payload("fuzz_json", "nested_deep", '{"a":' * 50 + '1' + '}' * 50, "50 levels deep", "medium"),
        Payload("fuzz_json", "huge_array", '[' + ','.join(['1'] * 10000) + ']', "10k element array", "medium"),
        Payload("fuzz_json", "duplicate_keys", '{"a":1,"a":2,"a":3}', "Duplicate keys", "low"),
        Payload("fuzz_json", "unicode_key", '{"\u0000key": "value"}', "Null byte in key", "medium"),
        Payload("fuzz_json", "proto_pollution", '{"__proto__": {"admin": true}}', "Prototype pollution via JSON", "high"),
    ]


def _url_fuzz() -> list[Payload]:
    return [
        Payload("fuzz_url", "javascript_proto", "javascript:alert(1)", "JavaScript protocol", "high"),
        Payload("fuzz_url", "data_proto", "data:text/html,<script>alert(1)</script>", "Data URI", "high"),
        Payload("fuzz_url", "double_slash", "//evil.com", "Protocol-relative URL", "medium"),
        Payload("fuzz_url", "backslash", "http://evil.com\\@good.com", "Backslash confusion", "medium"),
        Payload("fuzz_url", "at_sign", "http://evil.com%40good.com", "Encoded @ in URL", "medium"),
        Payload("fuzz_url", "unicode_domain", "http://evil\u2025com", "Unicode domain confusion", "medium"),
        Payload("fuzz_url", "long_url", "http://example.com/" + "a" * 10000, "Very long URL", "medium"),
    ]


def _email_fuzz() -> list[Payload]:
    return [
        Payload("fuzz_email", "basic_invalid", "not-an-email", "Missing @ and domain", "low"),
        Payload("fuzz_email", "no_domain", "user@", "Missing domain", "low"),
        Payload("fuzz_email", "no_local", "@domain.com", "Missing local part", "low"),
        Payload("fuzz_email", "double_at", "user@@domain.com", "Double @", "low"),
        Payload("fuzz_email", "special_chars", "user+tag@domain.com", "Plus addressing", "low"),
        Payload("fuzz_email", "long_local", "a" * 256 + "@domain.com", "Very long local part", "medium"),
        Payload("fuzz_email", "injection", "user@domain.com\r\nBCC: victim@evil.com", "Email header injection", "high"),
    ]


def _filename_fuzz() -> list[Payload]:
    return [
        Payload("fuzz_filename", "dot_dot", "../../../etc/passwd", "Path traversal", "high"),
        Payload("fuzz_filename", "null_extension", "file.txt\x00.jpg", "Null byte extension", "high"),
        Payload("fuzz_filename", "windows_reserved", "CON", "Windows reserved name", "medium"),
        Payload("fuzz_filename", "double_extension", "payload.php.jpg", "Double extension", "medium"),
        Payload("fuzz_filename", "hidden_file", ".htaccess", "Hidden/config file", "medium"),
        Payload("fuzz_filename", "long_name", "a" * 256 + ".txt", "Very long filename", "medium"),
        Payload("fuzz_filename", "unicode_name", "\u202efdp.exe", "RTL override in filename", "high"),
    ]
