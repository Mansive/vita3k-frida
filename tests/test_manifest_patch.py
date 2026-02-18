import xml.etree.ElementTree as ET

import repack


ANDROID_NS = "http://schemas.android.com/apk/res/android"
ATTR_EXTRACT_NATIVE_LIBS = f"{{{ANDROID_NS}}}extractNativeLibs"
ATTR_VERSION_CODE = f"{{{ANDROID_NS}}}versionCode"


def _extract_application_value(xml_text: str, attr_name: str) -> str | None:
    root = ET.fromstring(xml_text)
    application = root.find("application")
    assert application is not None
    return application.get(attr_name)


def _extract_manifest_value(xml_text: str, attr_name: str) -> str | None:
    root = ET.fromstring(xml_text)
    return root.get(attr_name)


def test_patch_manifest_sets_extract_native_libs_true() -> None:
    xml_input = (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<manifest xmlns:android="http://schemas.android.com/apk/res/android">'
        '<application android:extractNativeLibs="false" />'
        "</manifest>"
    )

    xml_output = repack.patch_manifest(xml_input)

    assert _extract_application_value(xml_output, ATTR_EXTRACT_NATIVE_LIBS) == "true"


def test_patch_manifest_sets_version_code_override() -> None:
    xml_input = (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<manifest xmlns:android="http://schemas.android.com/apk/res/android" android:versionCode="21">'
        "<application />"
        "</manifest>"
    )

    xml_output = repack.patch_manifest(xml_input, android_version_code=3923)

    assert _extract_manifest_value(xml_output, ATTR_VERSION_CODE) == "3923"
    assert _extract_application_value(xml_output, ATTR_EXTRACT_NATIVE_LIBS) == "true"
