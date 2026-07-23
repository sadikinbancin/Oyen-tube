# Oyen Motion AI V0.5 validation diagnostics

- Source commit: `22ff726bc68550f4270ae12188563da39717721c`
- Outcome: `success`

```text
test_compiler_creates_fixed_tracks_root_and_face_events (test_oyen_2d_director.Oyen2DMotionDirectorTests.test_compiler_creates_fixed_tracks_root_and_face_events) ... ok
test_generated_blender_script_is_valid_and_library_only (test_oyen_2d_director.Oyen2DMotionDirectorTests.test_generated_blender_script_is_valid_and_library_only) ... ok
test_manifest_matches_code_contract (test_oyen_2d_director.Oyen2DMotionDirectorTests.test_manifest_matches_code_contract) ... ok
test_rejects_overlapping_locomotion (test_oyen_2d_director.Oyen2DMotionDirectorTests.test_rejects_overlapping_locomotion) ... ok
test_rejects_unknown_action_and_arbitrary_code_field (test_oyen_2d_director.Oyen2DMotionDirectorTests.test_rejects_unknown_action_and_arbitrary_code_field) ... ok
test_run_prompt_uses_library_actions_and_no_unrequested_wave (test_oyen_2d_director.Oyen2DMotionDirectorTests.test_run_prompt_uses_library_actions_and_no_unrequested_wave) ... ok
test_wave_only_when_requested (test_oyen_2d_director.Oyen2DMotionDirectorTests.test_wave_only_when_requested) ... ok
test_generated_motion_rig_script_is_valid_python (test_oyen_bridge.OyenBridgeTests.test_generated_motion_rig_script_is_valid_python) ... ok
test_worker_zip_contains_required_files (test_oyen_bridge.OyenBridgeTests.test_worker_zip_contains_required_files) ... ok
test_indonesian_run_prompt_moves_forward_not_sideways (test_oyen_motion_ai.OyenMotionAITests.test_indonesian_run_prompt_moves_forward_not_sideways) ... ok
test_plan_ends_at_requested_duration (test_oyen_motion_ai.OyenMotionAITests.test_plan_ends_at_requested_duration) ... ok
test_wave_is_only_added_when_requested (test_oyen_motion_ai.OyenMotionAITests.test_wave_is_only_added_when_requested) ... ok
test_find_blender_accepts_explicit_executable (test_oyen_runtime.OyenRuntimeTests.test_find_blender_accepts_explicit_executable) ... ok
test_find_blender_fails_cleanly (test_oyen_runtime.OyenRuntimeTests.test_find_blender_fails_cleanly) ... ok
test_prepare_script_contains_runtime_paths_rig_and_motion_proof (test_oyen_runtime.OyenRuntimeTests.test_prepare_script_contains_runtime_paths_rig_and_motion_proof) ... ok

----------------------------------------------------------------------
Ran 15 tests in 0.028s

OK
OYEN_V05_SCRIPT_OK bytes=46537 provider=Local fallback clips=['run', 'look', 'angry'] note=Local prompt parser

```
