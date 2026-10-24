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
    assert "if not ModelsTouched then ModelsPage.Values[I]" in text
    assert "if ModelIds[I] = 'large-v3-turbo-q8_0' then ModelsPage.CheckListBox.ItemCaption" in text
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
