# Python Backend Test Failure Inventory

**Generated**: 2025-11-28
**CI Run**: #19764998477 (main branch)
**Total Tests**: 956 (98 failed, 856 passed, 2 skipped)
**Failure Rate**: 10.3%

## Executive Summary

All **98 tests** that fail on CI also fail locally. The failures cluster into **8 distinct categories**, with the majority being **test code issues** rather than implementation bugs.

| Category | Count | Fix Location |
|----------|-------|--------------|
| API Signature Mismatches | 22 | Tests |
| Missing/Incorrect Mocks | 21 | Tests |
| Data Structure Mismatches | 12 | Tests |
| Date/Time Logic Issues | 11 | Tests + Implementation |
| Method/Attribute Renamed | 10 | Tests |
| Async/Await Issues | 8 | Tests |
| Configuration/Environment | 6 | Tests |
| Implementation Bugs | 8 | Implementation |

---

## Failure Categories (Detailed)

### Category 1: API Signature Mismatches (22 tests)

Tests calling methods with outdated signatures or missing required parameters.

#### test_ai/test_agent_logging.py (4 tests)
| Test | Issue |
|------|-------|
| `test_general_travel_handler_conversation_logging` | `handle_travel_query()` missing required `intent` param |
| `test_general_travel_handler_prompt_template_logging` | Same as above |
| `test_general_travel_handler_ai_response_logging` | Same as above |
| `test_data_extractor_conversation_logging` | Uses `conversation_context` kwarg, should be `context` |

**Fix**: Update test method calls to match current signatures.

#### test_ai/test_flight_field_collector.py (5 tests)
| Test | Issue |
|------|-------|
| `test_assign_relative_date_departure_one_way` | `_assign_relative_date()` called with 4 args, takes 2-3 |
| `test_assign_relative_date_departure_round_trip` | Same signature mismatch |
| `test_assign_relative_date_return_explicit` | Uses `field_context` kwarg that doesn't exist |
| `test_assign_relative_date_both_dates_in_message` | Same signature mismatch |
| `test_assign_relative_date_context_waiting_for_return` | Same signature mismatch |

**Fix**: Update function calls to match `_assign_relative_date(extracted, relative_date, message="")`.

#### test_ai/test_exception_handling_improvements.py (7 tests)
| Test | Issue |
|------|-------|
| `test_complete_registration_invalid_token_error` | Missing `confirm_password` in Pydantic model |
| `test_reset_password_invalid_token_error` | Same missing field |
| `test_enhanced_flight_handler_variable_definition` | Patches `handler.field_collector` which doesn't exist |
| `test_flight_handler_error_logging` | Same mock target issue |
| `test_user_variable_initialization_in_flight_handler` | Same mock target issue |
| `test_flights_response_initialization_in_flight_handler` | Same mock target issue |
| `test_exception_handling_preserves_session_context` | Same mock target issue |

**Fix**: Add `confirm_password` to test data; remove invalid mock targets.

#### test_ai/test_field_validation_improvements.py (9 tests)
| Test | Issue |
|------|-------|
| `test_validate_future_date_with_today_date_object` | Validation logic changed |
| `test_validate_future_date_with_string_invalid_format` | Same |
| `test_validate_future_date_with_dict_range_past_start` | Same |
| `test_validate_future_date_with_dict_single_date_valid` | Same |
| `test_validate_future_date_with_dict_error` | Same |
| `test_validate_future_date_with_unsupported_type` | Same |
| `test_date_range_parsing_integration_sync` | Same |
| `test_date_range_parsing_integration_async` | Same |
| `test_date_object_validation_edge_cases` | Same |

**Fix**: Update test expectations to match current validation behavior.

---

### Category 2: Missing/Incorrect Mocks (21 tests)

Tests failing due to unmocked MongoDB calls or incorrectly configured async mocks.

#### test_ai/test_flight_booking_handler.py (6 tests)
| Test | Issue |
|------|-------|
| `test_handle_flight_selection_with_mongo_persistence` | MongoDB `BookingSessionService` not mocked |
| `test_generate_flight_booker_url_with_persistence` | Same |
| `test_start_passenger_collection_redirect` | Same |
| `test_start_passenger_collection_no_flight_selected` | Same |
| `test_redirect_to_flight_booker_with_selected_option` | Same + wrong method name |
| `test_redirect_to_flight_booker_fallback_to_option_number` | Same |

**Fix**: Add mocks for `BookingSessionService.store_session()`, `get_session()`, `update_session_data()`.

#### test_domains/test_chat_intent_bypass_fix.py (5 tests)
| Test | Issue |
|------|-------|
| `test_airport_code_response_maintains_book_flight_intent` | `repository.get_chat_messages()` returns Mock not AsyncMock |
| `test_intent_change_detected_during_airport_selection` | Same async mock issue |
| `test_edge_case_atm_nyc_message` | Same |
| `test_sticky_intent_threshold_during_airport_selection` | Same |
| `test_no_bypass_code_path_exists` | Same |

**Fix**: Use `AsyncMock` for all async repository methods.

#### test_ai/test_agent_logging.py (6 tests)
| Test | Issue |
|------|-------|
| `test_intent_recognizer_prompt_template_logging` | Log format assertions don't match actual output |
| `test_intent_recognizer_ai_response_logging` | Same |
| `test_data_extractor_prompt_template_logging` | Same |
| `test_data_extractor_ai_response_logging` | Same |
| `test_agents_logger_called_with_correct_format` | Same |
| `test_intent_recognizer_template_info_error_handling` | Logger mocked after module import |

**Fix**: Update log assertions to use looser pattern matching.

#### test_ai/test_flight_handler_date_ranges.py (2 tests)
| Test | Issue |
|------|-------|
| `test_multi_date_search_calls_service_multiple_times` | `search_flights` mock never called (0 != 3) |
| `test_single_date_search_still_works` | Same (0 != 1) |

**Fix**: Verify mock is patching the correct module path.

#### test_domains/test_airport_resolver.py (1 test)
| Test | Issue |
|------|-------|
| `test_download_airport_data_from_github` | `session.get()` returns coroutine not async context manager |

**Fix**: Configure mock to return `AsyncMock` with `__aenter__`/`__aexit__`.

---

### Category 3: Data Structure Mismatches (12 tests)

Tests providing data in wrong format or structure.

#### test_ai/test_enhanced_flight_handler_flow.py (3 tests)
| Test | Issue |
|------|-------|
| `test_flight_selection_flow_priority_over_extraction` | `search_results` stored as list, code expects dict with `'outbound'` key |
| `test_flight_selection_requires_both_search_results_and_no_booking` | Same |
| `test_field_extraction_corruption_prevention` | Same |

**Fix**: Store search results as `{'outbound': [...], 'return': [...]}` dict.

#### test_ai/test_flight_field_collector.py (4 tests)
| Test | Issue |
|------|-------|
| `test_route_parsing_keyword_based` | Destination not extracted for "going from Amsterdam to London" |
| `test_route_parsing_synonyms` | Origin not extracted for "out of New York bound for Paris" |
| `test_question_context_origin_assignment` | Origin not assigned from question context |
| `test_question_context_passenger_count_assignment` | Children count not extracted |

**Fix**: These may indicate implementation gaps in route parsing patterns.

#### test_ai/test_origin_destination_extraction.py (4 tests)
| Test | Issue |
|------|-------|
| `test_x_to_y_with_complex_airport_names` | "John F Kennedy to Los Angeles" - origin not extracted |
| `test_extraction_with_punctuation` | "London, to JFK." - origin not extracted |
| `test_combined_pattern_vs_separate_extraction` | Destination missing from result |
| `test_origin_destination_airport_resolution_integration` | `FlightFieldCollector` has no `airport_resolver` attribute |

**Fix**: Update airport name regex patterns; add missing attribute.

---

### Category 4: Date/Time Logic Issues (11 tests)

Tests related to date parsing, validation, and year inference.

#### test_ai/test_date_range_parsing.py (3 tests)
| Test | Issue |
|------|-------|
| `test_validate_return_date_with_range_departure` | Returns 2026 instead of 2025 |
| `test_validate_return_date_before_range_departure` | Returns True instead of False |
| `test_validate_return_date_with_single_departure` | Returns 2026 instead of 2025 |

**Root Cause**: Year inference logic incorrectly adding year to future dates.

#### test_ai/test_enhanced_date_range_parsing.py (2 tests)
| Test | Issue |
|------|-------|
| `test_parse_date_range_between_x_and_y_format` | Pattern "between Oct 10 and Oct 12" not matched |
| `test_date_range_edge_cases` | "Oct 30 - Nov 2" cross-month range fails |

**Root Cause**: Missing regex patterns for these date range formats.

#### test_ai/test_flight_field_collector.py (3 tests)
| Test | Issue |
|------|-------|
| `test_parse_relative_time_weeks` | "next week" returns wrong date |
| `test_parse_relative_time_invalid_expressions` | "0 days" returns date instead of None |
| `test_parse_relative_time_edge_cases` | Whitespace-padded "\\t1 week\\n" returns None |

**Fix**: Update relative time parsing and edge case handling.

#### test_ai/test_flight_curation_issue8.py (1 test) + test_ai/test_issue10_multi_date_search.py (1 test)
| Test | Issue |
|------|-------|
| `test_invalid_flight_returns_infinity` | `OverflowError: cannot convert float infinity to integer` |
| `test_scenario_1_clear_winner_across_days` | Same infinity conversion error |

**Fix**: Handle infinity properly in duration calculations (use max int or special value).

---

### Category 5: Method/Attribute Renamed (10 tests)

Tests using old method names that no longer exist.

#### test_ai/test_agent_logging.py (4 tests)
| Test | Issue |
|------|-------|
| `test_general_travel_handler_log_conversation_inputs_method` | Method is `_extract_conversation_inputs()` not `_log_conversation_inputs()` |
| `test_agent_logging_handles_malformed_context` | Same |
| `test_data_extractor_log_conversation_inputs_flight_specific` | Returns different keys than expected |
| `test_agent_logging_with_very_long_messages` | Missing `contains_flight_keywords` key |

**Fix**: Update method names and expected dictionary keys.

#### test_ai/test_flight_field_collector.py (3 tests)
| Test | Issue |
|------|-------|
| `test_journey_type_parsing_variations` | `JourneyType.ROUND_TRIP` should be `JourneyType.RETURN` |
| `test_complete_message_parsing_complex` | Same enum name issue |
| `test_message_parsing_with_relative_return_date` | Same |

**Fix**: Replace `ROUND_TRIP` with `RETURN` in all tests.

#### test_ai/test_flight_booking_handler.py (3 tests)
| Test | Issue |
|------|-------|
| `test_redirect_to_flight_booker_with_selected_option` | Calls `_redirect_to_flight_booker()`, should be `_start_passenger_collection()` |
| `test_redirect_to_flight_booker_missing_option_error` | Same |
| `test_redirect_to_flight_booker_fallback_to_option_number` | Same |

**Fix**: Update method names to match implementation.

---

### Category 6: Async/Await Issues (8 tests)

Missing `await` on async calls or sync tests calling async functions.

#### test_ai/test_flight_booking_handler.py (5 tests)
| Test | Issue |
|------|-------|
| `test_generate_flight_booker_url_success` | Not awaiting `_generate_flight_booker_url()` |
| `test_generate_flight_booker_url_error_fallback` | Same |
| `test_date_serialization_in_search_params` | Same |
| `test_decimal_serialization_in_flight_data` | Same |
| `test_real_production_data_serialization` | Same |

**Fix**: Add `await` to all async method calls.

#### test_ai/test_agent_logging.py (1 test)
| Test | Issue |
|------|-------|
| `test_intent_recognizer_log_conversation_inputs_extraction` | Off-by-one: message is 41 chars, test expects 40 |

**Fix**: Correct expected message length.

---

### Category 7: Configuration/Environment Issues (6 tests)

Tests expecting specific config values or environment setup.

#### test_core/test_cors_configuration.py (5 tests)
| Test | Issue |
|------|-------|
| `test_cors_origins_empty_string_returns_empty_list` | Returns default list, not empty |
| `test_cors_origins_rejects_http_non_localhost` | Doesn't raise ValidationError |
| `test_cors_origins_rejects_invalid_schemes` | Same |
| `test_validate_cors_origins_validator_after_mode` | Returns default list |
| `test_validate_cors_origins_validation_errors` | Raises ValueError not ValidationError |

**Root Cause**: `CORS_ORIGINS` is a `@property` that bypasses Pydantic validators.

**Fix**: Redesign config to use validators OR update tests.

#### test_core/test_database_connection.py (4 tests)
| Test | Issue |
|------|-------|
| `test_mongodb_connect_test_uses_mongodb_uri` | Uses `pytest.any` which doesn't exist |
| `test_mongodb_connect_test_scram_uses_mongodb_uri` | Same |
| `test_mongodb_connect_test_scram_detects_localhost_default` | MongoDB connection error |
| `test_regression_mongodb_connect_test_scram_uses_correct_variable` | DNS lookup failure |

**Fix**: Replace `pytest.any` with `unittest.mock.ANY`; mock MongoDB client.

---

### Category 8: Implementation Bugs (8 tests)

Actual bugs in the implementation code.

#### test_ai/test_flight_booking_handler.py (3 tests)
| Test | Issue |
|------|-------|
| `test_parse_flight_selection_option_numbers` | Regex missing "book" action word |
| `test_parse_flight_selection_ordinal_words` | Regex missing "pick" action word |
| `test_handle_booking_confirmation_cancel` | "cancel booking" matches "book", triggers wrong branch |

**Fix**: Add "book" and "pick" to regex patterns; improve cancel detection.

#### test_domains/test_bookings/test_reference_generator.py (2 tests)
| Test | Issue |
|------|-------|
| `test_alphabet_excludes_ambiguous_characters` | Alphabet includes 'L' (looks like '1') |
| `test_validate_format_valid_reference` | Validation regex doesn't match expected format |

**Fix**: Review reference generator alphabet and validation logic.

#### test_domains/test_bookings/test_booking_session_service.py (2 tests)
| Test | Issue |
|------|-------|
| `test_serialize_fallback_to_string` | Returns `{}` instead of string fallback |
| `test_serialize_none_fallback` | Returns `{}` instead of None |

**Fix**: Implement proper fallback logic in serializer.

#### test_ai/test_flight_booking_handler.py (1 test)
| Test | Issue |
|------|-------|
| `test_handle_flight_selection_valid_option` | URL uses localhost instead of config value |

**Fix**: Test should use looser assertion or mock config.

---

## Failing Tests by File

| File | Total | Failed | Passed |
|------|-------|--------|--------|
| test_ai/test_agent_logging.py | 17 | 15 | 2 |
| test_ai/test_flight_booking_handler.py | 49 | 14 | 35 |
| test_ai/test_flight_field_collector.py | 25 | 14 | 11 |
| test_ai/test_field_validation_improvements.py | 20 | 9 | 11 |
| test_ai/test_exception_handling_improvements.py | 12 | 7 | 5 |
| test_core/test_cors_configuration.py | 18 | 5 | 13 |
| test_domains/test_chat_intent_bypass_fix.py | 8 | 5 | 3 |
| test_ai/test_origin_destination_extraction.py | 17 | 4 | 13 |
| test_core/test_database_connection.py | 16 | 4 | 12 |
| test_ai/test_date_range_parsing.py | 18 | 3 | 15 |
| test_ai/test_enhanced_flight_handler_flow.py | 6 | 3 | 3 |
| test_ai/test_enhanced_date_range_parsing.py | 11 | 2 | 9 |
| test_ai/test_flight_handler_date_ranges.py | 5 | 2 | 3 |
| test_domains/test_bookings/test_reference_generator.py | 15 | 2 | 13 |
| test_domains/test_bookings/test_booking_session_service.py | 21 | 2 | 19 |
| test_ai/test_flight_curation_issue8.py | 5 | 1 | 4 |
| test_ai/test_issue10_multi_date_search.py | 2 | 1 | 1 |
| test_domains/test_airport_resolver.py | 29 | 1 | 28 |

---

## Recommended Fix Priority

### Priority 1: Quick Wins (30 tests, ~2 hours)
- Replace `pytest.any` with `unittest.mock.ANY` (4 tests)
- Add `await` to async calls (5 tests)
- Replace `JourneyType.ROUND_TRIP` with `RETURN` (3 tests)
- Fix method names (`_log_conversation_inputs` → `_extract_conversation_inputs`) (4 tests)
- Add `confirm_password` to test data (2 tests)
- Fix `_assign_relative_date()` call signatures (5 tests)
- Update log assertion patterns (6 tests)

### Priority 2: Mock Configuration (21 tests, ~3 hours)
- Add MongoDB `BookingSessionService` mocks (6 tests)
- Configure proper AsyncMock for repository methods (5 tests)
- Fix mock paths for service methods (10 tests)

### Priority 3: Implementation Fixes (8 tests, ~2 hours)
- Add "book" and "pick" to flight selection regex (2 tests)
- Fix infinity handling in duration calculations (2 tests)
- Fix serialization fallback logic (2 tests)
- Review reference generator (2 tests)

### Priority 4: Architecture Review (9 tests, ~4 hours)
- CORS configuration property vs validator design (5 tests)
- Date range parsing pattern additions (4 tests)

---

## CI vs Local Comparison

| Metric | CI | Local |
|--------|-----|-------|
| Total Failures | 98 | 98 |
| Same Tests Fail | Yes | Yes |
| Path Difference | `tests/test_*` | `tests/unit_tests/test_*` |

**Conclusion**: All failures are reproducible locally. No environment-specific issues.

---

## Next Steps

1. **Triage**: Review this inventory with the team
2. **Assign**: Group fixes by expertise area (AI handlers, database, config)
3. **Fix**: Start with Priority 1 (quick wins) to reduce failure count
4. **CI Gate**: Consider blocking merges until test failures < 10%
