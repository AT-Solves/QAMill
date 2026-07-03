# QAMill JSON Repair Module
# Handles malformed JSON from LLMs with robust repair mechanisms

import json
import logging
import re
from typing import Any, Optional, Tuple

logger = logging.getLogger(__name__)


class JSONRepairError(Exception):
    """Raised when JSON cannot be repaired"""
    pass


class JSONRepair:
    """Robust JSON repair for malformed LLM responses"""

    @staticmethod
    def repair(text: str, max_attempts: int = 5) -> Tuple[Any, bool]:
        """
        Attempt to repair and parse JSON with multiple strategies.

        Returns:
            Tuple of (parsed_object, was_repaired)
        """
        # Try direct parse first
        try:
            return json.loads(text), False
        except json.JSONDecodeError as e:
            logger.debug(f"Initial JSON parse failed: {e}")

        repaired_text = text
        attempt = 0

        # Try multiple repair strategies
        while attempt < max_attempts:
            attempt += 1
            logger.debug(f"Repair attempt {attempt}/{max_attempts}")

            try:
                # Strategy 1: Close unclosed structures
                repaired_text = JSONRepair._close_structures(repaired_text)

                # Strategy 2: Fix quotes
                repaired_text = JSONRepair._fix_quotes(repaired_text)

                # Strategy 3: Remove trailing commas
                repaired_text = JSONRepair._remove_trailing_commas(repaired_text)

                # Strategy 4: Normalize whitespace
                repaired_text = JSONRepair._normalize_whitespace(repaired_text)

                # Try to parse
                result = json.loads(repaired_text)
                logger.info(f"JSON repaired successfully on attempt {attempt}")
                return result, True

            except json.JSONDecodeError as e:
                logger.debug(f"Attempt {attempt} failed: {e}")
                if attempt == max_attempts:
                    raise JSONRepairError(f"Could not repair JSON after {max_attempts} attempts: {e}")

        raise JSONRepairError("JSON repair failed")

    @staticmethod
    def _close_structures(text: str) -> str:
        """Close unclosed braces and brackets"""
        open_braces = text.count('{') - text.count('}')
        open_brackets = text.count('[') - text.count(']')
        open_parens = text.count('(') - text.count(')')

        # Add closing characters
        if open_braces > 0:
            text += '}' * open_braces
            logger.debug(f"Added {open_braces} closing braces")

        if open_brackets > 0:
            text += ']' * open_brackets
            logger.debug(f"Added {open_brackets} closing brackets")

        if open_parens > 0:
            text += ')' * open_parens
            logger.debug(f"Added {open_parens} closing parentheses")

        return text

    @staticmethod
    def _fix_quotes(text: str) -> str:
        """Fix broken quotes and escaped characters"""
        # Fix common quote issues
        # Unmatched quotes in strings
        text = re.sub(r'"\s*:\s*"([^"]*)"([^"]*?)(?=\s*[,}\]])', r'"\1\2"', text)

        # Fix escaped quotes
        text = text.replace('\\"', '"')
        text = text.replace("'", '"')

        # Fix unclosed strings at end
        if text.rstrip()[-1] not in ('}', ']', '"'):
            # Check if we're in the middle of a string
            last_quote_pos = text.rfind('"')
            last_close_pos = max(text.rfind('}'), text.rfind(']'))

            if last_quote_pos > last_close_pos:
                # We're in an unclosed string
                text = text[:last_quote_pos] + '"' + text[last_quote_pos:]
                logger.debug("Fixed unclosed string")

        return text

    @staticmethod
    def _remove_trailing_commas(text: str) -> str:
        """Remove trailing commas before closing braces/brackets"""
        text = re.sub(r',(\s*[}\]])', r'\1', text)
        logger.debug("Removed trailing commas")
        return text

    @staticmethod
    def _normalize_whitespace(text: str) -> str:
        """Normalize problematic whitespace"""
        # Remove extra whitespace around colons
        text = re.sub(r'\s*:\s*', ': ', text)

        # Remove extra whitespace around commas (but keep one)
        text = re.sub(r',\s*', ', ', text)

        # Remove extra newlines
        text = re.sub(r'\n\s*\n', '\n', text)

        return text

    @staticmethod
    def validate_test_cases(data: Any) -> Tuple[bool, Optional[str]]:
        """
        Validate test case format.

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not isinstance(data, list):
            return False, "Expected list of test cases"

        if len(data) == 0:
            return False, "Empty test case list"

        required_fields = {"id", "title", "priority", "steps", "expected"}

        for i, case in enumerate(data):
            if not isinstance(case, dict):
                return False, f"Test case {i} is not a dictionary"

            missing_fields = required_fields - set(case.keys())
            if missing_fields:
                return False, f"Test case {i} missing fields: {missing_fields}"

            # Validate field types
            if not isinstance(case.get("steps"), list):
                return False, f"Test case {i}: steps must be a list"

            if len(case.get("steps", [])) == 0:
                return False, f"Test case {i}: steps cannot be empty"

        return True, None

    @staticmethod
    def safe_parse(
        text: str,
        expect_list: bool = True,
        max_attempts: int = 5
    ) -> Optional[Any]:
        """
        Safely parse with validation.

        Returns:
            Parsed object or None if parsing fails
        """
        try:
            data, was_repaired = JSONRepair.repair(text, max_attempts)

            if expect_list:
                if not isinstance(data, list):
                    logger.error("Expected list but got: " + type(data).__name__)
                    return None

                is_valid, error_msg = JSONRepair.validate_test_cases(data)
                if not is_valid:
                    logger.error(f"Validation failed: {error_msg}")
                    return None

            if was_repaired:
                logger.info(f"JSON was repaired, validation passed")

            return data

        except JSONRepairError as e:
            logger.error(f"JSON repair failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in JSON parsing: {e}")
            return None
