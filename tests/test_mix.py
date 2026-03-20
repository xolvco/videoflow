"""Tests for videoflow.mix — AudioTrack, VolumeRamp, AudioMix."""

from __future__ import annotations

import unittest

from videoflow.mix import AudioMix, AudioTrack, MixError, VolumeRamp


# ---------------------------------------------------------------------------
# AudioTrack validation
# ---------------------------------------------------------------------------

class TestAudioTrack(unittest.TestCase):

    def test_valid_track(self):
        t = AudioTrack("music.mp3", level=0.8)
        self.assertAlmostEqual(t.level, 0.8)

    def test_level_zero_is_valid(self):
        AudioTrack("music.mp3", level=0.0)

    def test_level_one_is_valid(self):
        AudioTrack("music.mp3", level=1.0)

    def test_level_above_one_raises(self):
        with self.assertRaises(ValueError):
            AudioTrack("music.mp3", level=1.1)

    def test_level_below_zero_raises(self):
        with self.assertRaises(ValueError):
            AudioTrack("music.mp3", level=-0.1)

    def test_fade_in_zero_is_valid(self):
        AudioTrack("music.mp3", fade_in_ms=0)

    def test_fade_out_zero_is_valid(self):
        AudioTrack("music.mp3", fade_out_ms=0)

    def test_negative_fade_in_raises(self):
        with self.assertRaises(ValueError):
            AudioTrack("music.mp3", fade_in_ms=-1)

    def test_negative_fade_out_raises(self):
        with self.assertRaises(ValueError):
            AudioTrack("music.mp3", fade_out_ms=-1)

    def test_defaults(self):
        t = AudioTrack("music.mp3")
        self.assertAlmostEqual(t.level, 1.0)
        self.assertEqual(t.fade_in_ms, 0)
        self.assertEqual(t.fade_out_ms, 0)


# ---------------------------------------------------------------------------
# VolumeRamp validation
# ---------------------------------------------------------------------------

class TestVolumeRamp(unittest.TestCase):

    def test_valid_ramp(self):
        r = VolumeRamp(track=0, at_ms=10_000, to_level=0.5, over_ms=2_000)
        self.assertEqual(r.track, 0)

    def test_to_level_zero_is_valid(self):
        VolumeRamp(track=0, at_ms=0, to_level=0.0)

    def test_to_level_one_is_valid(self):
        VolumeRamp(track=0, at_ms=0, to_level=1.0)

    def test_to_level_above_one_raises(self):
        with self.assertRaises(ValueError):
            VolumeRamp(track=0, at_ms=0, to_level=1.01)

    def test_to_level_below_zero_raises(self):
        with self.assertRaises(ValueError):
            VolumeRamp(track=0, at_ms=0, to_level=-0.01)

    def test_over_ms_zero_raises(self):
        with self.assertRaises(ValueError):
            VolumeRamp(track=0, at_ms=0, to_level=0.5, over_ms=0)

    def test_over_ms_negative_raises(self):
        with self.assertRaises(ValueError):
            VolumeRamp(track=0, at_ms=0, to_level=0.5, over_ms=-1)

    def test_default_over_ms(self):
        r = VolumeRamp(track=0, at_ms=0, to_level=0.5)
        self.assertEqual(r.over_ms, 500)


# ---------------------------------------------------------------------------
# AudioMix validation
# ---------------------------------------------------------------------------

class TestAudioMixValidation(unittest.TestCase):

    def test_empty_tracks_raises(self):
        with self.assertRaises(ValueError):
            AudioMix(tracks=[])

    def test_ramp_references_valid_track(self):
        t = AudioTrack("music.mp3")
        r = VolumeRamp(track=0, at_ms=1000, to_level=0.0)
        mix = AudioMix(tracks=[t], ramps=[r])
        self.assertEqual(len(mix.ramps), 1)

    def test_ramp_references_out_of_range_track_raises(self):
        t = AudioTrack("music.mp3")
        r = VolumeRamp(track=1, at_ms=1000, to_level=0.0)
        with self.assertRaises(ValueError):
            AudioMix(tracks=[t], ramps=[r])


# ---------------------------------------------------------------------------
# Filter chain construction — single track
# ---------------------------------------------------------------------------

class TestBuildFilterChainsSingleTrack(unittest.TestCase):

    def _mix(self, **kw):
        t = AudioTrack("music.mp3", **kw)
        return AudioMix(tracks=[t])

    def test_returns_parts_and_label(self):
        mix = self._mix()
        parts, label = mix.build_filter_chains(4)
        self.assertIsInstance(parts, list)
        self.assertEqual(label, "[aout]")

    def test_input_index_used_in_chain(self):
        mix = self._mix()
        parts, _ = mix.build_filter_chains(4)
        self.assertTrue(any("[4:a]" in p for p in parts))

    def test_level_in_chain(self):
        mix = self._mix(level=0.5)
        parts, _ = mix.build_filter_chains(4)
        self.assertTrue(any("volume=0.500000" in p for p in parts))

    def test_full_volume_in_chain(self):
        mix = self._mix(level=1.0)
        parts, _ = mix.build_filter_chains(4)
        self.assertTrue(any("volume=1.000000" in p for p in parts))

    def test_fade_in_added_when_set(self):
        mix = self._mix(fade_in_ms=500)
        parts, _ = mix.build_filter_chains(4)
        chain = " ".join(parts)
        self.assertIn("afade=t=in:st=0:d=0.500", chain)

    def test_no_fade_in_when_zero(self):
        mix = self._mix(fade_in_ms=0)
        parts, _ = mix.build_filter_chains(4)
        chain = " ".join(parts)
        self.assertNotIn("afade=t=in", chain)

    def test_fade_out_added_when_set(self):
        mix = AudioMix(
            tracks=[AudioTrack("music.mp3", fade_out_ms=1000)],
            duration_ms=10_000,
        )
        parts, _ = mix.build_filter_chains(4)
        chain = " ".join(parts)
        self.assertIn("afade=t=out", chain)
        self.assertIn("st=9.000", chain)

    def test_fade_out_skipped_without_duration_ms(self):
        mix = AudioMix(
            tracks=[AudioTrack("music.mp3", fade_out_ms=1000)],
            # duration_ms not set
        )
        parts, _ = mix.build_filter_chains(4)
        chain = " ".join(parts)
        self.assertNotIn("afade=t=out", chain)

    def test_single_track_uses_anull(self):
        mix = self._mix()
        parts, _ = mix.build_filter_chains(4)
        self.assertTrue(any("anull" in p for p in parts))

    def test_single_track_no_amix(self):
        mix = self._mix()
        parts, _ = mix.build_filter_chains(4)
        chain = " ".join(parts)
        self.assertNotIn("amix", chain)

    def test_output_label_is_aout(self):
        mix = self._mix()
        parts, _ = mix.build_filter_chains(4)
        # Last part should end with [aout]
        self.assertTrue(parts[-1].endswith("[aout]"))


# ---------------------------------------------------------------------------
# Filter chain construction — multiple tracks
# ---------------------------------------------------------------------------

class TestBuildFilterChainsMultiTrack(unittest.TestCase):

    def _two_track_mix(self):
        return AudioMix(tracks=[
            AudioTrack("music.mp3", level=0.8),
            AudioTrack("ambient.mp3", level=0.4),
        ])

    def test_two_tracks_uses_amix(self):
        mix = self._two_track_mix()
        parts, _ = mix.build_filter_chains(4)
        chain = " ".join(parts)
        self.assertIn("amix=inputs=2", chain)

    def test_two_tracks_uses_correct_input_indices(self):
        mix = self._two_track_mix()
        parts, _ = mix.build_filter_chains(4)
        all_chains = " ".join(parts)
        self.assertIn("[4:a]", all_chains)
        self.assertIn("[5:a]", all_chains)

    def test_amix_normalize_zero(self):
        mix = self._two_track_mix()
        parts, _ = mix.build_filter_chains(4)
        chain = " ".join(parts)
        self.assertIn("normalize=0", chain)

    def test_output_label_is_aout(self):
        mix = self._two_track_mix()
        parts, label = mix.build_filter_chains(4)
        self.assertEqual(label, "[aout]")


# ---------------------------------------------------------------------------
# Volume ramp expression
# ---------------------------------------------------------------------------

class TestRampVolumeExpr(unittest.TestCase):

    def test_expr_is_string(self):
        r = VolumeRamp(track=0, at_ms=10_000, to_level=0.0, over_ms=2_000)
        expr = AudioMix._ramp_volume_expr(r)
        self.assertIsInstance(expr, str)

    def test_expr_contains_if(self):
        r = VolumeRamp(track=0, at_ms=10_000, to_level=0.0, over_ms=2_000)
        expr = AudioMix._ramp_volume_expr(r)
        self.assertIn("if(", expr)

    def test_expr_contains_t0(self):
        r = VolumeRamp(track=0, at_ms=10_000, to_level=0.0, over_ms=2_000)
        expr = AudioMix._ramp_volume_expr(r)
        self.assertIn("10.000", expr)

    def test_expr_contains_t1(self):
        r = VolumeRamp(track=0, at_ms=10_000, to_level=0.0, over_ms=2_000)
        expr = AudioMix._ramp_volume_expr(r)
        self.assertIn("12.000", expr)

    def test_expr_contains_target_level(self):
        r = VolumeRamp(track=0, at_ms=10_000, to_level=0.75, over_ms=500)
        expr = AudioMix._ramp_volume_expr(r)
        self.assertIn("0.750000", expr)

    def test_ramp_applied_to_correct_track(self):
        mix = AudioMix(
            tracks=[
                AudioTrack("a.mp3"),
                AudioTrack("b.mp3"),
            ],
            ramps=[VolumeRamp(track=1, at_ms=5_000, to_level=0.0, over_ms=1_000)],
        )
        parts, _ = mix.build_filter_chains(0)
        # Ramp expression should appear in b.mp3's chain (index 1), not a.mp3's (index 0)
        # Track 0 chain is parts[0]; track 1 chain is parts[1]
        self.assertNotIn("if(lt(t,5.000)", parts[0])
        self.assertIn("if(lt(t,5.000)", parts[1])


# ---------------------------------------------------------------------------
# Serialisation
# ---------------------------------------------------------------------------

class TestAudioMixSerialisation(unittest.TestCase):

    def _mix(self):
        return AudioMix(
            tracks=[
                AudioTrack("music.mp3", level=0.8, fade_in_ms=500, fade_out_ms=1000),
                AudioTrack("ambient.mp3", level=0.3),
            ],
            duration_ms=60_000,
            ramps=[
                VolumeRamp(track=0, at_ms=45_000, to_level=1.0, over_ms=2_000),
                VolumeRamp(track=1, at_ms=45_000, to_level=0.0, over_ms=1_000),
            ],
        )

    def test_to_dict_has_tracks(self):
        d = self._mix().to_dict()
        self.assertIn("tracks", d)
        self.assertEqual(len(d["tracks"]), 2)

    def test_to_dict_track_fields(self):
        d = self._mix().to_dict()
        t = d["tracks"][0]
        for key in ("input", "level", "fade_in_ms", "fade_out_ms"):
            self.assertIn(key, t)

    def test_to_dict_has_duration_ms(self):
        d = self._mix().to_dict()
        self.assertEqual(d["duration_ms"], 60_000)

    def test_to_dict_has_ramps(self):
        d = self._mix().to_dict()
        self.assertIn("ramps", d)
        self.assertEqual(len(d["ramps"]), 2)

    def test_to_dict_ramp_fields(self):
        d = self._mix().to_dict()
        r = d["ramps"][0]
        for key in ("track", "at_ms", "to_level", "over_ms"):
            self.assertIn(key, r)

    def test_to_dict_no_ramps_key_when_empty(self):
        mix = AudioMix(tracks=[AudioTrack("music.mp3")])
        d = mix.to_dict()
        self.assertNotIn("ramps", d)

    def test_to_dict_no_duration_when_none(self):
        mix = AudioMix(tracks=[AudioTrack("music.mp3")])
        d = mix.to_dict()
        self.assertNotIn("duration_ms", d)

    def test_from_dict_round_trip(self):
        original = self._mix()
        restored = AudioMix.from_dict(original.to_dict())

        self.assertEqual(len(restored.tracks), len(original.tracks))
        self.assertAlmostEqual(restored.tracks[0].level, original.tracks[0].level)
        self.assertEqual(restored.tracks[0].fade_in_ms, original.tracks[0].fade_in_ms)
        self.assertEqual(restored.duration_ms, original.duration_ms)
        self.assertEqual(len(restored.ramps), len(original.ramps))
        self.assertEqual(restored.ramps[0].at_ms, original.ramps[0].at_ms)
        self.assertAlmostEqual(restored.ramps[0].to_level, original.ramps[0].to_level)

    def test_from_dict_missing_tracks_raises(self):
        with self.assertRaises(MixError):
            AudioMix.from_dict({})

    def test_from_dict_invalid_level_raises(self):
        with self.assertRaises(MixError):
            AudioMix.from_dict({"tracks": [{"input": "a.mp3", "level": 2.0}]})

    def test_from_dict_no_ramps_key(self):
        d = {"tracks": [{"input": "music.mp3"}]}
        mix = AudioMix.from_dict(d)
        self.assertEqual(mix.ramps, [])


if __name__ == "__main__":
    unittest.main()
