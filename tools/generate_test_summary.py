import xml.etree.ElementTree as ET
from pathlib import Path


def generate_test_summary(junit_xml_path: str = "test-reports/junit.xml"):
    p = Path(junit_xml_path)
    if not p.exists():
        print("No junit xml found at", junit_xml_path)
        return
    tree = ET.parse(p)
    root = tree.getroot()
    total = int(root.attrib.get("tests", 0))
    failures = int(root.attrib.get("failures", 0))
    errors = int(root.attrib.get("errors", 0))
    skipped = int(root.attrib.get("skipped", 0))
    print(f"Tests: {total}, Failures: {failures}, Errors: {errors}, Skipped: {skipped}")


if __name__ == "__main__":
    generate_test_summary()
