"""The installer must preserve the catalog trust anchor and full protective terms."""

import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from installer.generate_iss import generate

ROOT = Path(__file__).resolve().parents[2]


def test_installer_generator_script_entry_point():
    result = subprocess.run(
        [sys.executable, str(ROOT / "installer/generate_iss.py"), "--help"],
        capture_output=True,
        timeout=20,
    )
    assert result.returncode == 0, result.stderr.decode()


def test_installer_uses_complete_licenses_and_unchanged_manifest(tmp_path):
    bundle = tmp_path / "bundle"
    (bundle / "resources").mkdir(parents=True)
    manifest = ROOT / "resources/models.json"
    shutil.copyfile(manifest, bundle / "resources/models.json")
    (bundle / "THIRD_PARTY_NOTICES.md").write_text("Audited app notices\n")
    output = tmp_path / "generated"
    script = generate(output, bundle)
    license_text = (output / "LICENSE.txt").read_text(encoding="utf-8")
    for source in (
        "LICENSE",
        "NOTICE",
        "packaging/licenses/microsoft/runtime-eula.txt",
        "packaging/licenses/inno/license.txt",
    ):
        assert (ROOT / source).read_text(encoding="utf-8") in license_text
    inputs = json.loads((output / "inputs.json").read_text())
    assert inputs["manifest_sha256"] == hashlib.sha256(manifest.read_bytes()).hexdigest()
    assert (
        inputs["license_sha256"]
        == hashlib.sha256((output / "LICENSE.txt").read_bytes()).hexdigest()
    )
    assert inputs["draft_only"]
    text = script.read_text(encoding="utf-8")
    assert "@@" not in text
    assert "PrivilegesRequired=lowest" in text
    assert "[LangOptions]\nDialogFontSize=10" in text
    assert "DialogFontSize" not in text.split("[LangOptions]", 1)[0]
    assert "DownloadTemporaryFile(" not in text
    assert "--retry-status" in text
    assert "--failure-log" in text
    assert "{localappdata}\\Dusty\\logs\\dusty.log" in text
    assert "--failure-marker" in text
    assert "LogFetchParentFailure(True, 0)" in text
    assert "LogFetchParentFailure(False, Code)" in text
    assert "SafeFetchLogPath(Folder + '\\dusty.log')" in text
    assert "FileExists(ExpandConstant('{tmp}\\fetch-retrying'))" in text
    assert "Connection lost, retrying..." in text
    assert "UninstallDelete" not in text  # No broad recursive deletion of user data.
    assert "--installer-test --backend " in text
    assert "function TestedDefaultId: String;" in text
    assert "ModelIds[Selected[I]] = RecommendedModel" in text
    assert text.count("'--installer-pass --model ' + Quoted(TestedDefaultId)") == 2
    assert "Stage := 4" in text  # Smallest model's additional CPU-only check.
    assert "@@" not in text
    assert "{param:ACCEPTTERMS|}" in text
    assert "{param:ALLOWDOWNLOAD|}" in text
    assert "{param:REMOVEMODELS|}" in text
    assert "CurStep = ssPostInstall" in text
    assert "function PrepareToInstall" in text
    assert "--installer-upgrade-root " in text
    uninstall = text.rsplit("function InitializeUninstall: Boolean;", 1)[1]
    assert uninstall.index("--installer-can-uninstall") < uninstall.index("if UninstallSilent")
    assert uninstall.index("--installer-can-uninstall") < uninstall.index("CreateCustomForm")
    assert "if UninstallSilent and (ExpandConstant('{param:DUSTYCONFIRM|}') <> 'yes')" in uninstall
    assert (
        "'UninstallString', Quoted(ExpandConstant('{uninstallexe}')) + ' /SILENT /DUSTYCONFIRM=yes'"
        in text
    )
    assert (
        "'QuietUninstallString', Quoted(ExpandConstant('{uninstallexe}'))"
        " + ' /SILENT /DUSTYCONFIRM=yes'" in text
    )
    icons = text.split("[Icons]", 1)[1].split("[CustomMessages]", 1)[0]
    assert "unins" not in icons.lower()
    assert icons.count('Filename: "{app}\\dusty\\dusty.exe"') == 2
    code = text.split("[Code]", 1)[1]
    assert not re.search(r"(?m)^\s*\[", code), "Inno parses leading arrays as sections"
    assert not re.search(r"(?m)^\s*#\d", code), "Inno parses leading character codes as directives"
    for key in ("MODEL_BEST_FOR", "MODEL_NOTE"):
        from dusty.app import messages as M

        expected = dict(getattr(M, key))
        # PM replaced the VAD row with an exact sentence including catalog size.
        # Validate that complete replacement, as well as every transcription row.
        manifest_data = json.loads(manifest.read_text())
        voice = M.INSTALLER["VoiceIncluded"].replace(
            "%1", M.format_size(manifest_data["vad"][0]["size_bytes"])
        )
        expected["silero-vad"] = voice
        for value in expected.values():
            assert value.replace("'", "''") in text
    assert "Finish without a model" in text
    assert "GraphicsCandidate" not in text
    assert "--probe-vulkan --out" in text
    initial = text.split("procedure InitializeWizard;", 1)[1].split("procedure CurPageChanged", 1)[
        0
    ]
    assert initial.count("AddModelRow(") == len(manifest_data["models"])
    changed = text.split("procedure CurPageChanged", 1)[1].split("function NextButtonClick", 1)[0]
    probe = changed.split("if (Page = ModelsPage.ID) and not ProbeStarted", 1)[1].split(
        "if Page = DownloadPage.ID", 1
    )[0]
    assert "Stage := -4" in probe and "ExtractTemporaryFiles" not in probe
    assert "and not WizardSilent then begin" in probe
    assert "WizardForm.NextButton.Enabled := False" in probe
    assert "ModelViewport.Enabled := False" in probe
    assert "Checking this computer..." in text
    # Plan from verified files, not the selection: installed files are still
    # checked/tested, but never count towards transfer bytes or consent names.
    assert 'Pos(\'"silero-vad":"installed"\'' in text
    assert "Pos('\"' + ModelIds[I] + '\":\"installed\"'" in text
    credit = text.split("if CurrentDownloadWanted then begin", 1)[1].split(
        "DownloadIndex := DownloadIndex + 1", 1
    )[0]
    assert "CompletedModelBytes" in credit
    assert (
        "(Stage >= 1) and (Stage <= 2) and CurrentDownloadWanted"
        in text.split("procedure ShowAmount;", 1)[1]
    )
    assert "Check and test" in text
    assert "if (Stage = -4) or (Stage = -1)" in text
    assert "--installer-cancel-part --model " in text
    assert "DeleteFile(ExpandConstant('{localappdata}" not in text
    partial = text.split("procedure CleanupActivePartial", 1)[1].split("procedure WithoutClick", 1)[
        0
    ]
    assert "(not Success) or (Code <> 0)" in partial and "PartialKept" in partial
    without = text.split("procedure WithoutClick", 1)[1].split("procedure ModelsClick", 1)[0]
    assert without.index("CleanupActivePartial;") < without.index("Stage := 5;")
    cancel = text.split("procedure CancelButtonClick", 1)[1].split("function GetCustom", 1)[0]
    assert cancel.count("CleanupActivePartial;") == 2  # Busy and failed/idle normal close.
    failure = text.split("procedure Failure", 1)[1].split("function CurrentId", 1)[0]
    assert "RetryButton.Visible := True" in failure
    assert "WizardForm.NextButton.Enabled := False" in failure
    assert "Meter.Position := CompletedModelBytes * 100 div TotalModelBytes" in failure
    assert "Action := NewButton" not in text
    assert "BackButtonClick" in text and "ReturnModelsRequested := Result" in text
    assert "if not ModelsTouched then SetModelChecked(I," in text
    assert "if ModelIds[I] = 'large-v3-turbo-q8_0' then ModelTitles[I].Caption" in text
    assert "FileSize64" in text and "Amount.Caption" in text
    assert "runasoriginaluser" in text and "skipifsilent" in text
    assert "(CurPageID = wpFinished) and not Busy" in text
    assert "Cancel.Default := True" in text
    assert "WizardForm.CancelButton.OnClick := @SetupCancelClick" in text
    assert "WizardForm.OnCloseQuery := @SetupCloseQuery" in text
    assert "WizardForm.CancelButton.Visible := True" in text
    assert "SetupEnableMenuItem(SetupSystemMenu" in text
    stop = text.split("procedure FinishStopped;\n", 1)[1].split("procedure ModelsClick", 1)[0]
    assert "WizardForm.RunList.Checked[I] := False" in stop
    assert "ExitProcess" not in stop
    assert "if StopRequested then Result := 130" in text
    size_reader = text.split("function UninstallModelSize", 1)[1].split("procedure ReviewTick", 1)[
        0
    ]
    assert "Result := UTF8Decode(S)" in size_reader  # Keep the shared nonbreaking unit space.
    assert "Flags: unchecked" not in text.split("[Tasks]", 1)[1].split("[Messages]", 1)[0]
    assert "close all other applications" not in text
    for key in (
        "GpuSelfTestFailed",
        "SetupComplete",
        "SetupCompletePlural",
        "FinishedWithout",
        "RemoveModelsHelp",
        "OpenDustyNow",
    ):
        assert M.INSTALLER[key] in text


def test_installer_rejects_tampered_catalog(tmp_path):
    bundle = tmp_path / "bundle"
    (bundle / "resources").mkdir(parents=True)
    data = json.loads((ROOT / "resources/models.json").read_text())
    data["models"][0]["sha256"] = "invalid"
    (bundle / "resources/models.json").write_text(json.dumps(data))
    with pytest.raises(ValueError):
        generate(tmp_path / "generated", bundle)


def test_download_consent_cases_only_name_and_count_the_needed_files(tmp_path):
    from dusty.app import messages as M

    bundle = tmp_path / "bundle"
    (bundle / "resources").mkdir(parents=True)
    shutil.copyfile(ROOT / "resources/models.json", bundle / "resources/models.json")
    (bundle / "THIRD_PARTY_NOTICES.md").write_text("Audited app notices\n")
    text = generate(tmp_path / "generated", bundle).read_text(encoding="utf-8")
    data = json.loads((ROOT / "resources/models.json").read_text())
    models = data["models"]
    consent = text.split("function ConsentText: String;", 1)[1].split(
        "function DownloadText: String;", 1
    )[0]
    # Every possible needed subset, including VAD alone and no VAD. Installed
    # selected models cannot inflate any of these literal consent totals.
    for mask in range(1, 1 << (len(models) + 1)):
        entries = models + data["vad"]
        chosen = [entry for i, entry in enumerate(entries) if mask & (1 << i)]
        names = [
            M.VOICE_MODEL if e["id"] == "silero-vad" else M.MODEL_TECHNICAL[e["id"]] for e in chosen
        ]
        expected = M.DOWNLOAD_CONFIRM.format(
            names=M.join_names(names), size=M.format_size(sum(e["size_bytes"] for e in chosen))
        )
        assert f"{mask}: Result := '{expected.replace(chr(39), chr(39) * 2)}';" in consent
    assert M.join_names(["A", "B", "C"]) == "A, B and C"
    assert M.join_names(["A", "B"]) == "A and B"
    assert "if NeededMask = 0 then begin Result := AlreadyText; Exit; end;" in consent
    assert "are already downloaded. Dusty will check and test them." in text


def test_model_cards_and_skip_without_false_success(tmp_path):
    bundle = tmp_path / "bundle"
    (bundle / "resources").mkdir(parents=True)
    shutil.copyfile(ROOT / "resources/models.json", bundle / "resources/models.json")
    (bundle / "THIRD_PARTY_NOTICES.md").write_text("Audited notices")
    text = generate(tmp_path / "generated", bundle).read_text()
    assert "MemoryNotice := NewLabel(ModelsPage.Surface, 0, 38" in text
    assert "ModelViewport.SetBounds(0, ScaleY(40)" in text
    assert "Row.BevelOuter := bvNone; Row.BevelKind := bkFlat" in text
    assert "ModelTitles[Index].Font.Style := [fsBold]" in text
    assert (
        "ModelChecks[Index].SetBounds(ScaleX(12), ScaleY(8), Row.Width - ScaleX(24), ScaleY(24))"
        in text
    )
    assert "ModelTitles[Index] := ModelChecks[Index]" in text
    assert "ModelViewport.CenterOnShow := False" in text
    assert '"model_controls_fit":' in text
    assert "SkipModels=Skip for now" in text
    silent = text.split("if (CurStep = ssPostInstall) and WizardSilent", 1)[1]
    assert silent.index(
        "if SkipChoice.Checked then begin FinishedWithout := True; Exit;"
    ) < silent.index("DownloadClick(nil)")
    skipped = text.split("if SkipChoice.Checked then begin", 2)[2].split(
        "end else if DownloadStarted", 1
    )[0]
    assert "FinishedWithout := True" in skipped and "InstallationReady := True" not in skipped


def test_selftest_deadline_and_skip_card_disable_are_wired():
    text = (ROOT / "installer/wizard.iss").read_text()
    assert "Tick - TestBegan > TestDeadline" in text
    assert "Failure(True); Exit;" in text
    assert "self_test_timeout stage=" in text
    assert "ModelChecks[I].Enabled := not SkipChoice.Checked" in text


def test_silent_test_failure_has_nonzero_completion_without_false_gpu_result():
    text = (ROOT / "installer/wizard.iss").read_text(encoding="utf-8")
    silent = text.split("if (CurStep = ssPostInstall) and WizardSilent", 1)[1].split(
        "procedure CancelButtonClick", 1
    )[0]
    assert "SilentFailed := True" in silent
    assert "RaiseException" not in silent
    assert "Result := 10" in text.split("function GetCustomSetupExitCode", 1)[1]
    assert "(Page = DownloadPage.ID) and SilentFailed" in text
    assert "if StopRequested or SilentFailed then" in text
    timeout = text.split("Tick - TestBegan > TestDeadline", 1)[1].split(
        "if (Child.Process = 0)", 1
    )[0]
    assert "ReleaseChild; TestTimedOut := True" in timeout
    assert "SaveStringToFile" not in timeout
    assert "if IsTest and not TestTimedOut then" in text
    assert "(TestTimedOut and (Stage = 3) and not CpuRetry)" in text
    # Interactive failure still offers Retry and Finish without a model.
    failure = text.split("procedure Failure", 1)[1].split("function CurrentId", 1)[0]
    assert "RetryButton.Visible := True" in failure
    assert "WithoutButton.Visible := True" in failure


def test_installer_registers_only_five_current_user_wer_names_and_removes_them():
    template = (ROOT / "installer/dusty.iss.template").read_text(encoding="utf-8")
    wizard = (ROOT / "installer/wizard.iss").read_text(encoding="utf-8")
    assert (
        r"WerAddExcludedApplication@{syswow64}\wer.dll stdcall loadwithalteredsearchpath"
        in template
    )
    assert (
        r"WerRemoveExcludedApplication@{syswow64}\wer.dll stdcall loadwithalteredsearchpath"
        in template
    )
    names = wizard.split("function CrashExcludedName", 1)[1].split(
        "function RemoveCrashExclusions", 1
    )[0]
    import re

    assert re.findall(r"Result := '([^']+\.exe)'", names) == [
        "dusty.exe",
        "dusty-fetch.exe",
        "whisper-cli.exe",
        "ffmpeg.exe",
        "ffprobe.exe",
    ]
    assert "AddCrashExclusion(CrashExcludedName(I), False)" in wizard
    assert "RemoveCrashExclusion(CrashExcludedName(I), False)" in wizard
    assert "if Result then Result := RegisterCrashExclusions" in template
    assert "CurUninstallStep = usPostUninstall" in template
    assert "RemoveCrashExclusions(False)" in template
    assert "if not InstallationBegan then" in wizard
    assert "RemoveCrashExclusions(True)" in wizard
