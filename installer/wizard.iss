{ Shared production and review page controls. No installer HTTP calls. }
function InitializeUninstall: Boolean; forward;
procedure FinishStopped; forward;
procedure StopModelSetup(Confirm: Boolean); forward;
procedure DownloadClick(Sender: TObject); forward;
procedure ShowUninstallHelperUnavailable;
begin
  SuppressibleMsgBox(CustomMessage('UninstallHelperUnavailable'), mbError, MB_OK, IDOK);
end;

#ifdef ReviewOnly
procedure ReviewTick; forward;
procedure ReviewPopupTick(A, B, C, D: LongWord);
begin
  ReviewTick;
end;
#endif
#ifndef ReviewOnly
function CrashExcludedName(Index: Integer): String;
begin
  case Index of
    0: Result := 'dusty.exe';
    1: Result := 'dusty-fetch.exe';
    2: Result := 'whisper-cli.exe';
    3: Result := 'ffmpeg.exe';
    4: Result := 'ffprobe.exe';
  end;
end;

function RemoveCrashExclusions(OnlyNew: Boolean): Boolean;
var I: Integer;
begin
  Result := True;
  for I := 0 to 4 do
    if (not OnlyNew or AddedCrashExclusions[I]) and
       RegValueExists(HKCU, 'Software\Microsoft\Windows\Windows Error Reporting\ExcludedApplications', CrashExcludedName(I)) then
      if RemoveCrashExclusion(CrashExcludedName(I), False) <> 0 then Result := False;
end;

function RegisterCrashExclusions: Boolean;
var I: Integer;
begin
  Result := False;
  for I := 0 to 4 do begin
    AddedCrashExclusions[I] := not RegValueExists(HKCU,
      'Software\Microsoft\Windows\Windows Error Reporting\ExcludedApplications', CrashExcludedName(I));
    if AddCrashExclusion(CrashExcludedName(I), False) <> 0 then begin
      RemoveCrashExclusions(True);
      SuppressibleMsgBox(CustomMessage('CrashProtectionFailed'), mbError, MB_OK, IDOK);
      Exit;
    end;
  end;
  Result := True;
end;
#endif

function NewLabel(Parent: TWinControl; Top, Height: Integer; Text: String): TNewStaticText;
begin
  Result := TNewStaticText.Create(WizardForm);
  Result.Parent := Parent;
  Result.SetBounds(0, ScaleY(Top), Parent.Width, ScaleY(Height));
  Result.AutoSize := False;
  Result.WordWrap := True;
  Result.Caption := Text;
end;

procedure SetModelChecked(Index: Integer; Value: Boolean);
begin
  { VCL checkboxes also emit OnClick for programmatic selection changes. }
  UpdatingModels := True;
  ModelChecks[Index].Checked := Value;
  UpdatingModels := False;
end;

function NewButton(Parent: TWinControl; Left, Top, Width: Integer; Text: String;
  Handler: TNotifyEvent): TNewButton;
begin
  Result := TNewButton.Create(WizardForm);
  Result.Parent := Parent;
  Result.SetBounds(ScaleX(Left), ScaleY(Top), ScaleX(Width), ScaleY(32));
  Result.Caption := Text;
  Result.OnClick := Handler;
end;

function AlreadyText: String;
var I, Mask, Bit: Integer;
begin
  Mask := 0; Bit := 1;
  for I := 0 to GetArrayLength(ModelIds) - 1 do begin
    if ModelChecks[I].Checked then Mask := Mask + Bit;
    Bit := Bit * 2;
  end;
  Result := '';
  case Mask of
@@ALREADY_CASES@@
  end;
end;

function ConsentText: String;
begin
  if NeededMask = 0 then begin Result := AlreadyText; Exit; end;
  Result := '';
  case NeededMask of
@@CONSENT_CASES@@
  end;
end;

function DownloadText: String;
begin
  if NeededMask = 0 then begin Result := AlreadyText; Exit; end;
  Result := '';
  case NeededMask of
@@DOWNLOAD_CASES@@
  end;
end;

function CurrentDownloadWanted: Boolean;
begin
  if DownloadIndex >= GetArrayLength(Downloads) then begin Result := False; Exit; end;
  if Downloads[DownloadIndex] < 0 then Result := MissingVoice
  else Result := MissingModels[Downloads[DownloadIndex]];
end;

function SizeText(Bytes: Int64): String;
var Tenths: Int64; UnitName: String;
begin
  Tenths := (Bytes + 50000) div 100000;
  UnitName := CustomMessage('SizeMegabytes');
  if Tenths >= 10000 then begin
    Tenths := (Bytes + 50000000) div 100000000;
    UnitName := CustomMessage('SizeGigabytes');
  end;
  Result := FmtMessage(UnitName, [IntToStr(Tenths div 10) + '.' + IntToStr(Tenths mod 10)]);
end;

function TestedDefaultId: String;
var I: Integer;
begin
  Result := '';
  for I := 0 to GetArrayLength(Selected) - 1 do
    if ModelIds[Selected[I]] = RecommendedModel then Result := RecommendedModel;
  if (Result = '') and (GetArrayLength(Selected) > 0) then
    Result := ModelIds[Selected[0]];
end;

function SuccessText: String;
begin
  if GetArrayLength(Selected) > 1 then Result := CustomMessage('SetupCompletePlural')
  else Result := CustomMessage('SetupComplete');
end;

procedure ShowAmount;
var Bytes, Current: Int64; FileName: String;
begin
  Current := 0;
  if (Stage >= 1) and (Stage <= 2) and CurrentDownloadWanted then begin
    if Downloads[DownloadIndex] < 0 then FileName := '@@VAD_FILE@@'
    else FileName := ModelFiles[Downloads[DownloadIndex]];
    FileName := ExpandConstant('{localappdata}\Dusty\models\') + FileName;
    if Stage = 1 then FileName := FileName + '.part';
    if not FileSize64(FileName, Current) then Current := 0;
    if Downloads[DownloadIndex] < 0 then Bytes := @@VAD_BYTES@@
    else Bytes := ModelBytes[Downloads[DownloadIndex]];
    if Current > Bytes then Current := Bytes;
  end;
  Bytes := CompletedModelBytes + Current;
  Amount.Caption := FmtMessage(CustomMessage('DownloadAmount'), [SizeText(Bytes), SizeText(TotalModelBytes)]);
  if (Stage >= 0) and (Stage <= 2) and (TotalModelBytes > 0) then
    Meter.Position := Bytes * 100 div TotalModelBytes;
end;

procedure ReleaseChild;
begin
  if ChildJob <> 0 then CloseChild(ChildJob);
  if (Child.Process <> 0) and (Stage <> -1) then WaitChild(Child.Process, 2000);
  if Child.Process <> 0 then CloseChild(Child.Process);
  ChildJob := 0; Child.Process := 0;
end;

function StartChild(Exe, Arguments: String): Boolean;
var Info: TJobLimits32; Startup: TStartup; I: Integer;
begin
  ReleaseChild;
  for I := 0 to 111 do Info[I] := 0;
  Info[17] := $24;
  ChildJob := WinCreateJob(0, 0);
  Result := (ChildJob <> 0) and WinSetJob(ChildJob, 9, Info, 112);
  for I := 0 to 67 do Startup[I] := 0;
  Startup[0] := 68;
  if Result then Result := CreateChild(0, Quoted(Exe) + ' ' + Arguments,
    0, 0, False, $08000004, 0, ExtractFileDir(Exe), Startup, Child);
  if Result then Result := WinAssignJob(ChildJob, Child.Process);
  if Result then Result := ResumeChild(Child.Thread) <> $FFFFFFFF;
  if Child.Thread <> 0 then begin CloseChild(Child.Thread); Child.Thread := 0; end;
  if not Result then begin
    if Child.Process <> 0 then TerminateChild(Child.Process, 130);
    ReleaseChild;
  end;
end;

procedure Failure(IsTest: Boolean);
var S: AnsiString; GpuFailed: Boolean;
begin
  Busy := False;
  TestFailed := TestFailed or IsTest;
  GpuFailed := False;
  if IsTest and not TestTimedOut then
    if LoadStringFromFile(ExpandConstant('{tmp}\test-result.txt'), S) then
      GpuFailed := Pos('VULKAN', String(S)) > 0;
  if IsTest and GpuFailed then Phase.Caption := CustomMessage('GpuSelfTestFailed')
  else if IsTest then Phase.Caption := CustomMessage('SelfTestFailed')
  else Phase.Caption := CustomMessage('DownloadFailed');
  RetryButton.Visible := True;
  CpuButton.Visible := IsTest and (GpuFailed or (TestTimedOut and (Stage = 3) and not CpuRetry));
  WithoutButton.Visible := True;
  { The byte line describes download progress, even after a model test fails. }
  if TotalModelBytes > 0 then
    Meter.Position := CompletedModelBytes * 100 div TotalModelBytes;
  WizardForm.NextButton.Enabled := False;
end;

function CurrentId: String;
begin
  if Downloads[DownloadIndex] < 0 then Result := 'silero-vad'
  else Result := ModelIds[Downloads[DownloadIndex]];
end;

function CurrentName: String;
begin
  if Downloads[DownloadIndex] < 0 then Result := '@@VOICE_NAME@@'
  else Result := ModelNames[Downloads[DownloadIndex]];
end;

procedure BeginFetch(Command: String);
begin
  if Command = 'download' then Phase.Caption := FmtMessage(CustomMessage('DownloadWorking'), [CurrentName])
  else Phase.Caption := FmtMessage(CustomMessage('CheckingModel'), [CurrentName]);
  if not StartChild(ExpandConstant('{app}\dusty-fetch\dusty-fetch.exe'),
    Command + ' --id ' + Quoted(CurrentId) + ' --dest ' +
    Quoted(ExpandConstant('{localappdata}\Dusty\models')) + ' --manifest ' +
    Quoted(ExpandConstant('{app}\resources\models.json'))) then Failure(False);
end;

function SelfTestDeadline(Id: String; ProcessorOnly: Boolean): Int64;
begin
  Result := 360000;
  if Id = 'tiny' then Result := 120000
  else if (Id = 'small') or (Id = 'small.en') then Result := 180000
  else if Id = 'large-v3-turbo-q8_0' then Result := 300000;
  if ProcessorOnly then Result := Result + 120000;
end;

procedure BeginTest;
var Id, Name, Backend: String;
begin
  DeleteFile(ExpandConstant('{tmp}\test-result.txt'));
  if Stage = 4 then begin
    Id := ModelIds[Smallest]; Name := ModelNames[Smallest]; Backend := 'cpu';
    Phase.Caption := FmtMessage(CustomMessage('CpuTestWorking'), [Name]);
  end else begin
    Id := ModelIds[Selected[TestIndex]]; Name := ModelNames[Selected[TestIndex]];
    Backend := 'auto'; if CpuRetry then Backend := 'cpu';
    Phase.Caption := FmtMessage(CustomMessage('SelfTestWorking'), [
      Name, IntToStr(TestIndex + 1), IntToStr(GetArrayLength(Selected))]);
  end;
  TestTimedOut := False;
  TestBegan := Tick; TestDeadline := SelfTestDeadline(Id, Backend = 'cpu');
  { Disposable CI acceptance shortens, never lengthens, the real deadline. }
  if GetEnv('GITHUB_ACTIONS') = 'true' then
    if ((Stage = 3) and (ExpandConstant('{param:TESTSELFTESTTIMEOUT|}') = 'auto')) or
       ((Stage = 4) and (ExpandConstant('{param:TESTSELFTESTTIMEOUT|}') = 'cpu')) then
      TestDeadline := 1;
  if not StartChild(ExpandConstant('{app}\dusty\dusty.exe'),
    '--installer-test --backend ' + Backend + ' --model ' + Quoted(Id) +
    ' --out ' + Quoted(ExpandConstant('{tmp}\test-result.txt'))) then Failure(True);
end;

procedure FinishReady;
begin
  Busy := False; InstallationReady := True;
  Phase.Caption := SuccessText; Meter.Position := 100;
  RetryButton.Visible := False; CpuButton.Visible := False; WithoutButton.Visible := False;
  WizardForm.NextButton.Enabled := True;
  WizardForm.NextButton.Caption := SetupMessage(msgButtonNext);
  WizardForm.BackButton.Enabled := False;
end;

procedure ShowMemoryWarning;
var Memory: TMemoryStatus; I: Integer;
begin
  for I := 0 to GetArrayLength(ModelIds) - 1 do begin
    if not ModelsTouched then SetModelChecked(I, ModelIds[I] = RecommendedModel);
    if ModelIds[I] = RecommendedModel then ModelTitles[I].Caption := ModelRecommendedLabels[I]
    else ModelTitles[I].Caption := ModelLabels[I];
  end;
  ModelViewport.Enabled := True;
  if WizardForm.CurPageID = ModelsPage.ID then WizardForm.NextButton.Enabled := True;
  MemoryNotice.Caption := '';
  Memory.Length := 64;
  if WinMemoryStatus(Memory) then
    if Memory.TotalPhysical < @@MIN_RAM@@ then MemoryNotice.Caption := CustomMessage('LowMemory');
end;

procedure CheckExistingModels;
begin
  Stage := -3;
  if not StartChild(ProbeRoot + '\dusty\dusty.exe', '--installer-status --out ' +
    Quoted(ExpandConstant('{tmp}\model-status.json'))) then Stage := 0;
end;

procedure QueryDownloadPlan(StartNow: Boolean);
begin
  PlanStartRequested := StartNow;
  DownloadPlanReady := False; Busy := True; Stage := -5;
  Consent.Caption := CustomMessage('CheckingInstalled');
  Phase.Caption := ''; WizardForm.NextButton.Enabled := False;
  if not StartChild(ExpandConstant('{app}\dusty\dusty.exe'), '--installer-status --out ' +
    Quoted(ExpandConstant('{tmp}\download-plan.json'))) then Failure(False);
end;

procedure ApplyDownloadPlan(S: AnsiString);
var I, Bit: Integer;
begin
  SetArrayLength(MissingModels, GetArrayLength(ModelIds));
  NeededMask := 0; Bit := 1; TotalModelBytes := 0;
  for I := 0 to GetArrayLength(ModelIds) - 1 do begin
    MissingModels[I] := ModelChecks[I].Checked and (Pos('"' + ModelIds[I] + '":"installed"', String(S)) = 0);
    if MissingModels[I] then begin
      NeededMask := NeededMask + Bit;
      TotalModelBytes := TotalModelBytes + ModelBytes[I];
    end;
    Bit := Bit * 2;
  end;
  MissingVoice := Pos('"silero-vad":"installed"', String(S)) = 0;
  if MissingVoice then begin
    NeededMask := NeededMask + @@VOICE_BIT@@;
    TotalModelBytes := TotalModelBytes + @@VAD_BYTES@@;
  end;
  DownloadPlanReady := True;
end;

procedure PollChild(A, B, C, D: LongWord);
var Code: LongWord; I: Integer; Memory: TMemoryStatus; S: AnsiString; Prefix, Expected: Int64; Part: String;
begin
#ifdef ReviewOnly
  ReviewTick;
  Exit;
#endif
  { Return the page to Windows before extraction so every catalog row paints. }
  if Stage = -4 then begin
    if WizardForm.CurPageID <> ModelsPage.ID then Exit;
    Stage := 0;
    try ExtractTemporaryFiles('{tmp}\probe\*');
    except ShowMemoryWarning; Exit; end;
    ProbeRoot := ExpandConstant('{tmp}\probe');
    Stage := -1; ProbeBegan := Tick;
    if not StartChild(ProbeRoot + '\dusty\dusty.exe', '--probe-vulkan --out ' +
      Quoted(ExpandConstant('{tmp}\probe-result.json'))) then begin
      Stage := 0; ShowMemoryWarning;
    end;
    Exit;
  end;
  { Explicit, disposable CI acceptance: stop a real transfer after bytes arrive. }
  if WizardSilent and (GetEnv('GITHUB_ACTIONS') = 'true') and
     (ExpandConstant('{param:TESTCANCEL|}') = 'yes') and (Stage = 1) and not StopRequested then begin
    if Downloads[DownloadIndex] < 0 then begin Part := '@@VAD_FILE@@'; Expected := @@VAD_BYTES@@; end
    else begin Part := ModelFiles[Downloads[DownloadIndex]]; Expected := ModelBytes[Downloads[DownloadIndex]]; end;
    if FileSize64(ExpandConstant('{localappdata}\Dusty\models\') + Part + '.part', Prefix) then
      if (Prefix > 0) and (Prefix < Expected) then begin StopModelSetup(False); Exit; end;
  end;
  if DownloadStarted and Busy then ShowAmount;
  if (Stage = -1) and (Child.Process <> 0) and (Tick - ProbeBegan > 7000) then begin
    ReleaseChild; ShowMemoryWarning; CheckExistingModels; Exit;
  end;
  if ((Stage = 3) or (Stage = 4)) and Busy and (Child.Process <> 0) and
     (Tick - TestBegan > TestDeadline) then begin
    Log('self_test_timeout stage=' + IntToStr(Stage));
    ReleaseChild; TestTimedOut := True;
    { A timed-out Auto child has no confirmed backend result. Offer CPU retry
      without claiming that a graphics device was the cause. }
    Failure(True); Exit;
  end;
  if (Child.Process = 0) or (WaitChild(Child.Process, 0) <> 0) then Exit;
  Code := 1; ChildExit(Child.Process, Code); ReleaseChild;
  if Stage = -5 then begin
    if (Code <> 0) or not LoadStringFromFile(ExpandConstant('{tmp}\download-plan.json'), S) then begin Failure(False); Exit; end;
    ApplyDownloadPlan(S); Busy := False; Stage := 0;
    Consent.Caption := ConsentText;
    if NeededMask = 0 then WizardForm.NextButton.Caption := CustomMessage('CheckAndTest')
    else WizardForm.NextButton.Caption := CustomMessage('DownloadAction');
    WizardForm.NextButton.Enabled := True;
    if PlanStartRequested then DownloadClick(nil);
    Exit;
  end;
  if Stage = -3 then begin
    if (Code = 0) and LoadStringFromFile(ExpandConstant('{tmp}\model-status.json'), S) then
      for I := 0 to GetArrayLength(ModelIds) - 1 do
        if Pos('"' + ModelIds[I] + '":"damaged"', String(S)) > 0 then
          ModelTitles[I].Caption := ModelTitles[I].Caption + #13#10 + CustomMessage('NeedsDownload');
    Stage := 0; Exit;
  end;
  if Stage = -1 then begin
    ShowMemoryWarning; { Restore Small before applying a successful GPU result. }
    MemoryNotice.Caption := '';
    Memory.Length := 64;
    if WinMemoryStatus(Memory) then begin
      if Memory.TotalPhysical < @@MIN_RAM@@ then MemoryNotice.Caption := CustomMessage('LowMemory');
      if (Code = 0) and (Memory.TotalPhysical >= @@MIN_RAM@@) then
      begin
        RecommendedModel := 'large-v3-turbo-q8_0';
        for I := 0 to GetArrayLength(ModelIds) - 1 do begin
          if not ModelsTouched then SetModelChecked(I, ModelIds[I] = 'large-v3-turbo-q8_0');
          if ModelIds[I] = 'large-v3-turbo-q8_0' then ModelTitles[I].Caption := ModelRecommendedLabels[I]
          else ModelTitles[I].Caption := ModelLabels[I];
        end;
      end;
    end;
    CheckExistingModels;
    Exit;
  end;
  if Stage = 5 then begin
    if Code <> 0 then begin Failure(True); Exit; end;
    Busy := False; FinishedWithout := True;
    Phase.Caption := CustomMessage('FinishedWithout');
    WizardForm.NextButton.Enabled := True;
    WizardForm.NextButton.Caption := SetupMessage(msgButtonNext);
    if StopRequested then FinishStopped;
    Exit;
  end;
  if Stage = 6 then begin
    if Code = 0 then FinishReady else Failure(True);
    Exit;
  end;
  if Stage = -2 then begin
    if Code <> 0 then begin Failure(False); Exit; end;
    Stage := 0; BeginFetch('verify'); Exit;
  end;
  if Stage <= 2 then begin
    if (Stage = 0) and (Code <> 0) then begin
      if not CurrentDownloadWanted then begin Failure(False); Exit; end;
      Stage := 1; BeginFetch('download'); Exit;
    end;
    if Code <> 0 then begin Failure(False); Exit; end;
    if Stage = 1 then begin Stage := 2; BeginFetch('verify'); Exit; end;
    if CurrentDownloadWanted then begin
      if Downloads[DownloadIndex] < 0 then CompletedModelBytes := CompletedModelBytes + @@VAD_BYTES@@
      else CompletedModelBytes := CompletedModelBytes + ModelBytes[Downloads[DownloadIndex]];
    end;
    DownloadIndex := DownloadIndex + 1;
    ShowAmount;
    if DownloadIndex < GetArrayLength(Downloads) then begin Stage := 0; BeginFetch('verify'); end
    else begin Stage := 3; TestIndex := 0; BeginTest; end;
  end else begin
    if Code <> 0 then begin Failure(True); Exit; end;
    if LoadStringFromFile(ExpandConstant('{tmp}\test-result.txt'), S) then begin
      if Pos('VULKAN', String(S)) > 0 then Outcome.Caption := CustomMessage('GpuOutcome')
      else Outcome.Caption := CustomMessage('CpuOutcome');
    end;
    CpuRetry := False;
    if Stage = 4 then begin
      Stage := 6;
      if not StartChild(ExpandConstant('{app}\dusty\dusty.exe'),
        '--installer-pass --model ' + Quoted(TestedDefaultId)) then Failure(True);
    end
    else begin
      TestIndex := TestIndex + 1;
      Meter.Position := 40 + 50 * TestIndex div GetArrayLength(Selected);
      if TestIndex = GetArrayLength(Selected) then Stage := 4;
      BeginTest;
    end;
  end;
end;

procedure DownloadClick(Sender: TObject);
var I, Count: Integer;
begin
#ifdef ReviewOnly
  Exit; { Native preview controls must never start a real transfer. }
#endif
  if not DownloadPlanReady then begin QueryDownloadPlan(True); Exit; end;
  SetArrayLength(Selected, 0); Smallest := -1;
  for I := 0 to GetArrayLength(ModelIds) - 1 do if ModelChecks[I].Checked then begin
    Count := GetArrayLength(Selected); SetArrayLength(Selected, Count + 1); Selected[Count] := I;
    if Smallest < 0 then Smallest := I
    else if ModelBytes[I] < ModelBytes[Smallest] then Smallest := I;
  end;
  if GetArrayLength(Selected) = 0 then Exit;
  SetArrayLength(Downloads, GetArrayLength(Selected) + 1);
  for I := 0 to GetArrayLength(Selected) - 1 do Downloads[I] := Selected[I];
  Downloads[GetArrayLength(Selected)] := -1;
  CompletedModelBytes := 0;
  DownloadStarted := True; Consent.Caption := DownloadText;
  Meter.Visible := TotalModelBytes > 0; Amount.Visible := TotalModelBytes > 0;
  WizardForm.BackButton.Enabled := False;
  Busy := True; DownloadIndex := 0; Stage := -2;
  Meter.Position := 0; Outcome.Caption := '';
  ShowAmount;
  WizardForm.NextButton.Enabled := False;
  RetryButton.Visible := False; CpuButton.Visible := False; WithoutButton.Visible := False;
  if not StartChild(ExpandConstant('{app}\dusty\dusty.exe'), '--installer-prepare') then Failure(False);
end;

procedure RetryClick(Sender: TObject);
begin
#ifdef ReviewOnly
  Exit;
#endif
  RetryButton.Visible := False; CpuButton.Visible := False; WithoutButton.Visible := False;
  if Stage = -5 then begin QueryDownloadPlan(PlanStartRequested); Exit; end;
  Busy := True;
  if Stage = 5 then begin
    if not StartChild(ExpandConstant('{app}\dusty\dusty.exe'), '--installer-clear') then Failure(True);
  end else if Stage = 6 then begin
    if not StartChild(ExpandConstant('{app}\dusty\dusty.exe'),
      '--installer-pass --model ' + Quoted(TestedDefaultId)) then Failure(True);
  end else if Stage >= 3 then begin CpuRetry := False; BeginTest; end else DownloadClick(Sender);
end;

procedure CpuClick(Sender: TObject);
begin
#ifdef ReviewOnly
  Exit;
#endif
  RetryButton.Visible := False; CpuButton.Visible := False; WithoutButton.Visible := False;
  Busy := True; CpuRetry := True; BeginTest;
end;

procedure CleanupActivePartial;
var Code: Integer; Success: Boolean;
begin
  if (Stage < -2) or (Stage > 2) or
     (DownloadIndex < 0) or (DownloadIndex >= GetArrayLength(Downloads)) then Exit;
  Success := Exec(ExpandConstant('{app}\dusty\dusty.exe'),
    '--installer-cancel-part --model ' + Quoted(CurrentId),
    ExpandConstant('{app}\dusty'), SW_HIDE, ewWaitUntilTerminated, Code);
  if (not Success) or (Code <> 0) then
    SuppressibleMsgBox(CustomMessage('PartialKept'), mbInformation, MB_OK, IDOK);
end;

procedure WithoutClick(Sender: TObject);
begin
#ifdef ReviewOnly
  Exit;
#endif
  ReleaseChild;
  CleanupActivePartial;
  Stage := 5;
  if TestFailed then begin
    Busy := StartChild(ExpandConstant('{app}\dusty\dusty.exe'), '--installer-clear');
    if not Busy then begin Failure(True); Exit; end;
  end else begin
    Busy := False; FinishedWithout := True; Phase.Caption := CustomMessage('FinishedWithout');
    WizardForm.NextButton.Enabled := True;
    WizardForm.NextButton.Caption := SetupMessage(msgButtonNext);
  end;
  RetryButton.Visible := False;
  CpuButton.Visible := False; WithoutButton.Visible := False;
end;

procedure FinishStopped;
var I: Integer;
begin
  { Use Inno's ordinary finish/cleanup, with no postinstall application launch. }
  if WizardForm.CurPageID = ReturnModelsPage.ID then
    WizardForm.NextButton.OnClick(WizardForm.NextButton);
  if WizardForm.CurPageID = DownloadPage.ID then
    WizardForm.NextButton.OnClick(WizardForm.NextButton);
  if WizardForm.CurPageID = wpFinished then begin
    for I := 0 to WizardForm.RunList.Items.Count - 1 do WizardForm.RunList.Checked[I] := False;
    WizardForm.NextButton.OnClick(WizardForm.NextButton);
  end;
end;

procedure StopModelSetup(Confirm: Boolean);
begin
  if StopRequested then Exit;
  if Busy and Confirm then
    if SuppressibleMsgBox(CustomMessage('StopInstall'), mbConfirmation, MB_YESNO, IDNO) <> IDYES then Exit;
  StopRequested := True;
  if InstallationReady then begin ReleaseChild; FinishStopped; end
  else begin
    WithoutClick(nil);
    if not Busy and FinishedWithout then FinishStopped;
  end;
end;

procedure SetupCancelClick(Sender: TObject);
begin
#ifndef ReviewOnly
  if (WizardForm.CurPageID = DownloadPage.ID) or (WizardForm.CurPageID = ReturnModelsPage.ID) then begin
    StopModelSetup(True); Exit;
  end;
#endif
  OriginalCancelClick(Sender);
end;

procedure SetupCloseQuery(Sender: TObject; var CanClose: Boolean);
begin
#ifndef ReviewOnly
  if (WizardForm.CurPageID = DownloadPage.ID) or (WizardForm.CurPageID = ReturnModelsPage.ID) then begin
    CanClose := False;
    StopModelSetup(True); Exit;
  end;
#endif
  { Pinned native form has no OnCloseQuery handler. Leave earlier pages to its OnClose. }
end;

procedure EnableModelPageCancel;
begin
  WizardForm.CancelButton.Visible := True;
  WizardForm.CancelButton.Enabled := True;
  SetupEnableMenuItem(SetupSystemMenu(WizardForm.Handle, False), $F060, 0);
end;

procedure ModelsClick(Sender: TObject);
begin
  if UpdatingModels then Exit;
  ModelsTouched := True; DownloadPlanReady := False; FinishedWithout := False;
  SkipChoice.Checked := False;
  ShowMemoryWarning;
end;

procedure SkipModelsClick(Sender: TObject);
var I: Integer;
begin
  ModelsTouched := True; DownloadPlanReady := False; FinishedWithout := False;
  for I := 0 to GetArrayLength(ModelIds) - 1 do begin
    if SkipChoice.Checked then SetModelChecked(I, False);
    ModelChecks[I].Enabled := not SkipChoice.Checked;
    ModelDescriptions[I].Enabled := not SkipChoice.Checked;
  end;
end;

procedure AddModelRow(Index: Integer);
var Row: TPanel;
begin
  Row := TPanel.Create(WizardForm); Row.Parent := ModelViewport;
  Row.SetBounds(0, ScaleY(Index * 94), ModelsPage.SurfaceWidth - ScaleX(24), ScaleY(88));
  Row.BevelOuter := bvNone; Row.BevelKind := bkFlat;
  ModelChecks[Index] := TNewCheckBox.Create(WizardForm);
  ModelChecks[Index].Parent := Row;
  ModelChecks[Index].SetBounds(ScaleX(12), ScaleY(8), Row.Width - ScaleX(24), ScaleY(24));
  ModelChecks[Index].OnClick := @ModelsClick;
  ModelTitles[Index] := ModelChecks[Index];
  ModelTitles[Index].Caption := ModelLabels[Index];
  ModelTitles[Index].Font.Style := [fsBold];
  ModelDescriptions[Index] := NewLabel(Row, 33, 48, ModelDetails[Index]);
  ModelDescriptions[Index].Left := ScaleX(44); ModelDescriptions[Index].Width := Row.Width - ScaleX(56);
end;

procedure LicenseClick(Sender: TObject);
var File: String; S: AnsiString;
begin
  File := 'DUSTY-LICENSE.txt';
  if TNewButton(Sender).Tag = 1 then File := 'THIRD_PARTY_NOTICES.md';
  if TNewButton(Sender).Tag = 2 then File := 'MICROSOFT-LICENSE.txt';
  ExtractTemporaryFile(File);
  File := ExpandConstant('{tmp}\') + File;
  if LoadStringFromFile(File, S) then WizardForm.LicenseMemo.Text := UTF8Decode(S);
end;

procedure InitializeWizard;
var I: Integer; Requested: String; Button: TNewButton;
begin
#ifdef ReviewOnly
  InitialModelDpi := WindowDpi(WizardForm.Handle);
#endif
  RecommendedModel := 'small';
  ModelsPage := CreateCustomPage(wpLicense, CustomMessage('ChooseModels'),
    CustomMessage('ChooseModelsHelp'));
  MemoryNotice := NewLabel(ModelsPage.Surface, 0, 38, '');
  ModelViewport := CreateCustomForm(ModelsPage.SurfaceWidth, ScaleY(300), False, True);
  ModelViewport.CenterOnShow := False;
  ModelViewport.Parent := ModelsPage.Surface;
  ModelViewport.BorderStyle := bsNone; ModelViewport.AutoScroll := True;
  ModelViewport.SetBounds(0, ScaleY(40), ModelsPage.SurfaceWidth, ModelsPage.SurfaceHeight - ScaleY(150));
  ModelViewport.Visible := True;
  SetArrayLength(ModelChecks, @@MODEL_COUNT@@);
  SetArrayLength(ModelTitles, @@MODEL_COUNT@@);
  SetArrayLength(ModelDescriptions, @@MODEL_COUNT@@);
  SetArrayLength(ModelIds, @@MODEL_COUNT@@); SetArrayLength(ModelNames, @@MODEL_COUNT@@);
  SetArrayLength(ModelFiles, @@MODEL_COUNT@@); SetArrayLength(ModelLabels, @@MODEL_COUNT@@);
  SetArrayLength(ModelRecommendedLabels, @@MODEL_COUNT@@); SetArrayLength(ModelDetails, @@MODEL_COUNT@@);
  SetArrayLength(ModelBytes, @@MODEL_COUNT@@);
@@MODEL_SETUP@@
  SkipChoice := TNewCheckBox.Create(WizardForm); SkipChoice.Parent := ModelsPage.Surface;
  SkipChoice.SetBounds(0, ModelViewport.Top + ModelViewport.Height + ScaleY(4), ModelsPage.SurfaceWidth, ScaleY(24));
  SkipChoice.Caption := CustomMessage('SkipModels'); SkipChoice.OnClick := @SkipModelsClick;
  VoiceNotice := NewLabel(ModelsPage.Surface, 0, 36, @@VOICE_DESCRIPTION@@);
  VoiceNotice.Top := SkipChoice.Top + SkipChoice.Height + ScaleY(2);
  AccuracyNotice := NewLabel(ModelsPage.Surface, 0, 32, '@@MODEL_REVIEW@@');
  AccuracyNotice.Top := VoiceNotice.Top + VoiceNotice.Height;
  Requested := ExpandConstant('{param:MODELS|small}');
  for I := 0 to GetArrayLength(ModelIds) - 1 do begin
    SetModelChecked(I, Pos(',' + ModelIds[I] + ',', ',' + Requested + ',') > 0);
    if ModelIds[I] = 'small' then ModelTitles[I].Caption := ModelRecommendedLabels[I];
  end;
  ModelsTouched := ExpandConstant('{param:MODELS|}') <> '';
  SkipChoice.Checked := ExpandConstant('{param:SKIPMODELS|}') = 'yes';
  if SkipChoice.Checked then SkipModelsClick(nil);
  WizardForm.LicenseMemo.Height := WizardForm.LicenseMemo.Height - ScaleY(40);
  Button := NewButton(WizardForm.LicensePage, 0, 0, 145, CustomMessage('LicenseDusty'), @LicenseClick);
  Button.Top := WizardForm.LicenseMemo.Top + WizardForm.LicenseMemo.Height + ScaleY(4);
  Button := NewButton(WizardForm.LicensePage, 150, 0, 145, CustomMessage('LicenseNotices'), @LicenseClick);
  Button.Tag := 1; Button.Top := WizardForm.LicenseMemo.Top + WizardForm.LicenseMemo.Height + ScaleY(4);
  Button := NewButton(WizardForm.LicensePage, 300, 0, 180, CustomMessage('LicenseMicrosoft'), @LicenseClick);
  Button.Tag := 2; Button.Top := WizardForm.LicenseMemo.Top + WizardForm.LicenseMemo.Height + ScaleY(4);
#ifdef ReviewOnly
  ReturnModelsPage := CreateCustomPage(wpSelectTasks, CustomMessage('ChooseModels'), CustomMessage('ChooseModelsHelp'));
#else
  ReturnModelsPage := CreateCustomPage(wpInstalling, CustomMessage('ChooseModels'), CustomMessage('ChooseModelsHelp'));
#endif
  DownloadPage := CreateCustomPage(ReturnModelsPage.ID, CustomMessage('DownloadPage'), CustomMessage('DownloadPageHelp'));
  Consent := NewLabel(DownloadPage.Surface, 8, 52, '');
  Phase := NewLabel(DownloadPage.Surface, 68, 60, '');
  Meter := TNewProgressBar.Create(WizardForm); Meter.Parent := DownloadPage.Surface;
  Meter.SetBounds(0, ScaleY(132), DownloadPage.SurfaceWidth, ScaleY(24)); Meter.Max := 100;
  Amount := NewLabel(DownloadPage.Surface, 160, 24, '');
  Outcome := NewLabel(DownloadPage.Surface, 232, 68, '');
  RetryButton := NewButton(DownloadPage.Surface, 0, 192, 95, CustomMessage('Retry'), @RetryClick);
  CpuButton := NewButton(DownloadPage.Surface, 105, 192, 220, CustomMessage('RetryCpu'), @CpuClick);
  WithoutButton := NewButton(DownloadPage.Surface, 335, 192, 215, CustomMessage('FinishWithout'), @WithoutClick);
  RetryButton.Visible := False; CpuButton.Visible := False; WithoutButton.Visible := False;
  OriginalCancelClick := WizardForm.CancelButton.OnClick;
  WizardForm.CancelButton.OnClick := @SetupCancelClick;
  WizardForm.OnCloseQuery := @SetupCloseQuery;
  Timer := SetTimer(0, 0, 100, CreateCallback(@PollChild));
end;

function ModelPageY(Value: Integer): Integer;
begin
  Result := ScaleY(Value);
#ifdef ReviewOnly
  { Review windows can move between monitors; production Setup uses system DPI. }
  if InitialModelDpi > 0 then
    Result := Result * Integer(WindowDpi(WizardForm.Handle)) div InitialModelDpi;
#endif
end;

function ModelPageX(Value: Integer): Integer;
begin
  Result := ScaleX(Value);
#ifdef ReviewOnly
  if InitialModelDpi > 0 then
    Result := Result * Integer(WindowDpi(WizardForm.Handle)) div InitialModelDpi;
#endif
end;

procedure LayoutModels(Page: TWizardPage);
var I: Integer; Row: TPanel;
begin
  { Recompute after the notebook page has its final dimensions, not during creation. }
  MemoryNotice.SetBounds(0, 0, Page.SurfaceWidth, ModelPageY(38));
  ModelViewport.SetBounds(0, ModelPageY(40), Page.SurfaceWidth, Page.SurfaceHeight - ModelPageY(150));
  SkipChoice.SetBounds(0, ModelViewport.Top + ModelViewport.Height + ModelPageY(4), Page.SurfaceWidth, ModelPageY(24));
  VoiceNotice.SetBounds(0, SkipChoice.Top + SkipChoice.Height + ModelPageY(2), Page.SurfaceWidth, ModelPageY(36));
  AccuracyNotice.SetBounds(0, VoiceNotice.Top + VoiceNotice.Height, Page.SurfaceWidth, ModelPageY(32));
  ModelViewport.Font.Assign(WizardForm.Font);
  for I := 0 to GetArrayLength(ModelChecks) - 1 do begin
    Row := TPanel(ModelChecks[I].Parent);
    Row.SetBounds(0, ModelPageY(I * 94), Page.SurfaceWidth - ModelPageX(24), ModelPageY(88));
    ModelChecks[I].Font.Assign(WizardForm.Font); ModelChecks[I].Font.Style := [fsBold];
    ModelChecks[I].SetBounds(ModelPageX(12), ModelPageY(8), Row.Width - ModelPageX(24), ModelPageY(24));
    ModelDescriptions[I].Font.Assign(WizardForm.Font);
    ModelDescriptions[I].SetBounds(ModelPageX(44), ModelPageY(33), Row.Width - ModelPageX(56), ModelPageY(48));
  end;
end;

procedure CurPageChanged(Page: Integer);
var Code: Integer; I, Count: Integer; Mode: String;
begin
  if Page = ModelsPage.ID then LayoutModels(ModelsPage);
  if Page = ReturnModelsPage.ID then begin
    EnableModelPageCancel;
    ModelViewport.Parent := ReturnModelsPage.Surface;
    SkipChoice.Parent := ReturnModelsPage.Surface;
    VoiceNotice.Parent := ReturnModelsPage.Surface;
    AccuracyNotice.Parent := ReturnModelsPage.Surface;
    MemoryNotice.Parent := ReturnModelsPage.Surface;
    LayoutModels(ReturnModelsPage);
  end;
  if (Page = ModelsPage.ID) and not ProbeStarted and not WizardSilent then begin
    ProbeStarted := True;
#ifndef ReviewOnly
    MemoryNotice.Caption := CustomMessage('CheckingGraphics');
    for I := 0 to GetArrayLength(ModelIds) - 1 do begin
      if not ModelsTouched then SetModelChecked(I, False);
      ModelTitles[I].Caption := ModelLabels[I];
    end;
    ModelViewport.Enabled := False;
    WizardForm.NextButton.Enabled := False;
    Stage := -4; { PollChild starts extraction on a later event-loop turn. }
#endif
  end;
  if Page = DownloadPage.ID then begin
    EnableModelPageCancel;
    WizardForm.BackButton.Visible := True;
    WizardForm.BackButton.Enabled := not DownloadStarted;
    WizardForm.NextButton.Enabled := not DownloadStarted or InstallationReady or FinishedWithout;
    if SkipChoice.Checked then begin
      FinishedWithout := True;
      Consent.Caption := CustomMessage('SkippedModels');
      Phase.Caption := CustomMessage('FinishedWithout');
      WizardForm.NextButton.Enabled := True;
    end else if DownloadStarted then begin
      Consent.Caption := DownloadText;
      WizardForm.NextButton.Caption := SetupMessage(msgButtonNext);
    end else begin
      Consent.Caption := CustomMessage('CheckingInstalled');
#ifndef ReviewOnly
      QueryDownloadPlan(False);
#endif
    end;
    Meter.Visible := DownloadStarted and (TotalModelBytes > 0); Amount.Visible := Meter.Visible;
#ifdef ReviewOnly
    Mode := ExpandConstant('{param:REVIEWSTATE|consent}');
    Phase.Caption := CustomMessage('ReviewOnly');
    WizardForm.NextButton.Enabled := Mode = 'consent';
    if Mode <> 'consent' then begin
      DownloadStarted := True; Consent.Caption := DownloadText;
      Meter.Visible := True; Amount.Visible := True;
      TotalModelBytes := @@VAD_BYTES@@;
      SetArrayLength(Selected, 0);
      for I := 0 to GetArrayLength(ModelIds) - 1 do
        if ModelChecks[I].Checked then begin
          TotalModelBytes := TotalModelBytes + ModelBytes[I];
          Count := GetArrayLength(Selected); SetArrayLength(Selected, Count + 1); Selected[Count] := I;
        end;
      CompletedModelBytes := TotalModelBytes * 32 div 100; Stage := 3;
      if (Mode = 'test') or (Mode = 'test-failure') or (Mode = 'complete') then
        CompletedModelBytes := TotalModelBytes;
      ShowAmount;
      WizardForm.NextButton.Caption := SetupMessage(msgButtonNext);
      WizardForm.BackButton.Enabled := False;
    end;
    if Mode = 'download' then begin Phase.Caption := FmtMessage(CustomMessage('DownloadWorking'), [ModelNames[Selected[0]]]); Meter.Position := 32; end;
    if Mode = 'test' then begin Phase.Caption := FmtMessage(CustomMessage('SelfTestWorking'), [ModelNames[Selected[0]], '1', IntToStr(GetArrayLength(Selected))]); Meter.Position := 70; end;
    if Mode = 'failure' then Failure(False);
    if Mode = 'test-failure' then begin
      Failure(True); Phase.Caption := CustomMessage('GpuSelfTestFailed'); CpuButton.Visible := True;
    end;
    if Mode = 'complete' then FinishReady;
    if Mode = 'without' then begin Phase.Caption := CustomMessage('FinishedWithout'); WithoutButton.Visible := False; end;
    if Mode = 'uninstall' then begin
      Consent.Caption := CustomMessage('RemoveModelsHelp');
      Phase.Caption := FmtMessage(CustomMessage('RemoveModels'), ['@@REVIEW_MODELS_SIZE@@']);
    end;
#endif
  end;
  if Page = wpFinished then begin
    WizardForm.BackButton.Visible := False;
    if StopRequested or SilentFailed then
      for I := 0 to WizardForm.RunList.Items.Count - 1 do WizardForm.RunList.Checked[I] := False;
    if SilentFailed then begin
      if TestFailed then WizardForm.FinishedLabel.Caption := CustomMessage('SelfTestFailed')
      else WizardForm.FinishedLabel.Caption := CustomMessage('DownloadFailed');
    end else if FinishedWithout then WizardForm.FinishedLabel.Caption := CustomMessage('FinishedWithout')
    else WizardForm.FinishedLabel.Caption := SuccessText;
  end;
end;

function BackButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  if CurPageID = DownloadPage.ID then begin
    Result := not DownloadStarted;
    ReturnModelsRequested := Result;
  end;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var I, Count: Integer; Info: TJobLimits32;
begin
  Result := True;
  if StopRequested then Exit;
  if (CurPageID = ModelsPage.ID) or (CurPageID = ReturnModelsPage.ID) then begin
    if (Stage = -4) or (Stage = -1) then begin Result := False; Exit; end;
    Count := 0; for I := 0 to GetArrayLength(ModelIds) - 1 do if ModelChecks[I].Checked then Count := Count + 1;
    Result := (Count > 0) or SkipChoice.Checked;
    if not Result then MemoryNotice.Caption := CustomMessage('NeedModel');
    if Result then ReturnModelsRequested := False;
  end;
  if CurPageID = DownloadPage.ID then begin
    Result := InstallationReady or FinishedWithout;
#ifndef ReviewOnly
    if not DownloadStarted and not SkipChoice.Checked then begin DownloadClick(nil); Result := False; end;
#endif
  end;
#ifndef ReviewOnly
  if (CurPageID = wpFinished) and not Busy and (InstallationReady or FinishedWithout) then begin
    { No downloader/test remains. The explicitly requested GUI must outlive Setup. }
    ReleaseChild;
    for I := 0 to 111 do Info[I] := 0;
    if not WinSetJob(DownloadJob, 9, Info, 112) then begin
      if WizardForm.RunList.Items.Count > 0 then WizardForm.RunList.Checked[0] := False;
      SuppressibleMsgBox(CustomMessage('OpenFromStartMenu'), mbInformation, MB_OK, IDOK);
    end;
  end;
#endif
#ifdef ReviewOnly
  if CurPageID = DownloadPage.ID then Result := False;
  if CurPageID = wpReady then Result := False;
#endif
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var Code: Integer;
begin
  Result := '';
#ifndef ReviewOnly
  if DirExists(ExpandConstant('{app}\licenses\dusty')) then begin
    try
      ExtractTemporaryFiles('{tmp}\probe\*');
      if not Exec(ExpandConstant('{tmp}\probe\dusty\dusty.exe'),
        '--installer-upgrade-root ' + Quoted(ExpandConstant('{app}')), ExpandConstant('{tmp}\probe\dusty'), SW_HIDE,
        ewWaitUntilTerminated, Code) then Code := 1;
      if Code <> 0 then Result := CustomMessage('UpgradeFilesBlocked');
    except
      Result := CustomMessage('UpgradeFilesBlocked');
    end;
  end;
#endif
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssInstall then InstallationBegan := True;
#ifndef ReviewOnly
  if CurStep = ssDone then begin
    if not RegWriteStringValue(HKCU,
      'Software\Microsoft\Windows\CurrentVersion\Uninstall\{7B3110E8-7983-41AC-A0ED-F6EB13DBB72A}_is1',
      'UninstallString', Quoted(ExpandConstant('{uninstallexe}')) + ' /SILENT /DUSTYCONFIRM=yes') then
      RaiseException(CustomMessage('UninstallRegistrationFailed'));
    if not RegWriteStringValue(HKCU,
      'Software\Microsoft\Windows\CurrentVersion\Uninstall\{7B3110E8-7983-41AC-A0ED-F6EB13DBB72A}_is1',
      'QuietUninstallString', Quoted(ExpandConstant('{uninstallexe}')) + ' /SILENT /DUSTYCONFIRM=yes') then
      RaiseException(CustomMessage('UninstallRegistrationFailed'));
  end;
#endif
  if (CurStep = ssPostInstall) and WizardSilent then begin
    if SkipChoice.Checked then begin FinishedWithout := True; Exit; end;
    DownloadClick(nil);
    while Busy do begin Sleep(100); PollChild(0, 0, 0, 0); end;
    if StopRequested then Exit;
    if not InstallationReady then begin
      { Raising here makes Inno show its wizard even with /VERYSILENT.
        Complete file installation cleanly, retain verified files, return failure. }
      SilentFailed := True;
      Log('silent_setup_failed exit_code=10');
    end;
  end;
end;

procedure CancelButtonClick(CurPageID: Integer; var Cancel, Confirm: Boolean);
begin
  if Busy then begin
    Cancel := False; Confirm := False;
    if SuppressibleMsgBox(CustomMessage('StopInstall'), mbConfirmation, MB_YESNO, IDNO) = IDYES then begin
      ReleaseChild;
      CleanupActivePartial;
      Busy := False; Cancel := True;
    end;
  end else begin
    ReleaseChild;
    CleanupActivePartial;
  end;
end;

function GetCustomSetupExitCode: Integer;
begin
  if StopRequested then Result := 130
  else if SilentFailed then Result := 10
  else if InstallationReady or FinishedWithout then Result := 0 else Result := 10;
end;

function UninstallModelSize: String;
var Code: Integer; S: AnsiString;
begin
  Result := '@@ZERO_SIZE@@';
#ifdef ReviewOnly
  Result := '@@REVIEW_MODELS_SIZE@@'; Exit;
#endif
  if Exec(ExpandConstant('{app}\dusty\dusty.exe'), '--model-size --out ' +
    Quoted(ExpandConstant('{tmp}\model-size.txt')), '', SW_HIDE, ewWaitUntilTerminated, Code) then
    if (Code = 0) and LoadStringFromFile(ExpandConstant('{tmp}\model-size.txt'), S) then Result := UTF8Decode(S);
end;

#ifdef ReviewOnly
function ReviewScaled(Value, Numerator, Denominator: Integer): Integer;
begin
  if Value < 0 then Result := -((-Value * Numerator + Denominator div 2) div Denominator)
  else Result := (Value * Numerator + Denominator div 2) div Denominator;
end;

procedure SnapshotReviewControl(Control: TControl);
var I, Count: Integer;
begin
  Count := GetArrayLength(ReviewControls);
  SetArrayLength(ReviewControls, Count + 1);
  SetArrayLength(ReviewLefts, Count + 1); SetArrayLength(ReviewTops, Count + 1);
  SetArrayLength(ReviewWidths, Count + 1); SetArrayLength(ReviewHeights, Count + 1);
  ReviewControls[Count] := Control;
  ReviewLefts[Count] := Control.Left; ReviewTops[Count] := Control.Top;
  ReviewWidths[Count] := Control.Width; ReviewHeights[Count] := Control.Height;
  if Control is TWinControl then
    for I := 0 to TWinControl(Control).ControlCount - 1 do
      SnapshotReviewControl(TWinControl(Control).Controls[I]);
end;

procedure NormalizeReviewDpi(Numerator, Denominator: Integer);
var I: Integer; Control: TControl; Font: TFont;
begin
  SnapshotReviewControl(WizardForm);
  { Children first: explicit font changes detach ParentFont before their parents change. }
  for I := GetArrayLength(ReviewControls) - 1 downto 0 do begin
    Control := ReviewControls[I]; Font := nil;
    if Control is TNewStaticText then Font := TNewStaticText(Control).Font
    else if Control is TNewButton then Font := TNewButton(Control).Font
    else if Control is TNewCheckBox then Font := TNewCheckBox(Control).Font
    else if Control is TNewRadioButton then Font := TNewRadioButton(Control).Font
    else if Control is TNewCheckListBox then Font := TNewCheckListBox(Control).Font
    else if Control is TRichEditViewer then Font := TRichEditViewer(Control).Font
    else if Control is TSetupForm then Font := TSetupForm(Control).Font
    else if Control is TPanel then Font := TPanel(Control).Font;
    if Font <> nil then Font.Height := ReviewScaled(Font.Height, Numerator, Denominator);
  end;
  { Parent bounds first, then restore each child's scaled snapshot after anchor changes. }
  for I := 0 to GetArrayLength(ReviewControls) - 1 do begin
    Control := ReviewControls[I];
    if I = 0 then
      Control.SetBounds(ReviewLefts[I], ReviewTops[I],
        ReviewScaled(ReviewWidths[I], Numerator, Denominator),
        ReviewScaled(ReviewHeights[I], Numerator, Denominator))
    else
      Control.SetBounds(ReviewScaled(ReviewLefts[I], Numerator, Denominator),
        ReviewScaled(ReviewTops[I], Numerator, Denominator),
        ReviewScaled(ReviewWidths[I], Numerator, Denominator),
        ReviewScaled(ReviewHeights[I], Numerator, Denominator));
  end;
end;

procedure ReviewTick;
var Wanted, Metadata, Description, ImageFile: String; Page: Integer; Button: TNewButton;
  Bitmap: TBitmap; DC, Popup, ProcessId, SavedDpi: LongWord; I: Integer; Fits: Boolean; Bounds: TRect;
begin
  if ReviewDialogPending then begin
    if ReviewCaptured then Exit;
    Popup := ReviewActiveWindow;
    if (Popup = 0) or (Popup = WizardForm.Handle) or ((ReviewDialogItem(Popup, IDOK) = 0) and (ReviewDialogItem(Popup, IDCANCEL) = 0)) then Exit;
    ReviewWindowProcess(Popup, ProcessId);
    if ProcessId <> ReviewProcessId then Exit;
    if not ReviewPopupPositioned then begin
      ReviewPopupPositioned := True;
      { Move the actual PMv2 native dialog to the wizard's monitor. Windows
        recalculates its fonts and layout; never resize the resulting image. }
      if WindowDpi(Popup) <> WindowDpi(WizardForm.Handle) then begin
        SavedDpi := SetReviewDpiContext(-4);
        if SavedDpi = 0 then RaiseException(CustomMessage('ReviewDpiFailed'));
        try
          if not PositionReviewPopup(Popup, 0, WizardForm.Left + 40, WizardForm.Top + 60,
            0, 0, $0015) then RaiseException(CustomMessage('ReviewCaptureFailed'));
        finally
          SetReviewDpiContext(Integer(SavedDpi));
        end;
        Exit;
      end;
    end;
    if not ReviewClientRect(Popup, Bounds) then Exit;
    if (Bounds.Right <= 0) or (Bounds.Bottom <= 0) then Exit;
    { Capture only our real native error popup while its modal loop dispatches timers. }
    Bitmap := TBitmap.Create;
    try
      Bitmap.Width := Bounds.Right; Bitmap.Height := Bounds.Bottom;
      DC := ReviewDC(Popup);
      try
        if not CopyReviewBitmap(Bitmap.Canvas.Handle, 0, 0, Bitmap.Width, Bitmap.Height,
          DC, 0, 0, $00CC0020) then RaiseException(CustomMessage('ReviewCaptureFailed'));
        Bitmap.SaveToFile(ExpandConstant('{param:REVIEWBMP|}'));
      finally
        ReleaseReviewDC(Popup, DC);
      end;
    finally
      Bitmap.Free;
    end;
    SaveStringToFile(ExpandConstant('{param:REVIEWMETA|}'),
      '{"dpi":' + IntToStr(WindowDpi(Popup)) + ',"native_helper_message":true,"width":' +
      IntToStr(Bounds.Right) + ',"height":' + IntToStr(Bounds.Bottom) + '}', False);
    ReviewCaptured := True;
    Exit;
  end;
  if not ReviewPositioned then begin
    ReviewPositioned := True;
    if ExpandConstant('{param:REVIEWLEFT|}') <> '' then begin
      WizardForm.CenterOnShow := False;
      WizardForm.Left := StrToIntDef(ExpandConstant('{param:REVIEWLEFT|0}'), 0);
      WizardForm.Top := StrToIntDef(ExpandConstant('{param:REVIEWTOP|0}'), 0);
    end;
    Exit;
  end;
  if not ReviewDpiAdjusted then begin
    ReviewDpiAdjusted := True;
    { Setup uses custom startup scaling, not VCL's automatic Scaled property. }
    if (InitialModelDpi > 0) and (Integer(WindowDpi(WizardForm.Handle)) <> InitialModelDpi) then
      NormalizeReviewDpi(Integer(WindowDpi(WizardForm.Handle)), InitialModelDpi);
    Exit;
  end;
  if ReviewShown then begin
    if ReviewCaptured then Exit;
    ReviewCaptured := True;
    Metadata := ExpandConstant('{param:REVIEWMETA|}');
    Fits := (ModelViewport.Top >= MemoryNotice.Top + MemoryNotice.Height) and
      (SkipChoice.Top >= ModelViewport.Top + ModelViewport.Height) and
      (AccuracyNotice.Top + AccuracyNotice.Height <= ModelsPage.SurfaceHeight);
    for I := 0 to GetArrayLength(ModelChecks) - 1 do
      Fits := Fits and (ModelChecks[I].Top >= 0) and
        (ModelChecks[I].Top + ModelChecks[I].Height <= ModelChecks[I].Parent.Height) and
        (ModelChecks[I].Left + ModelChecks[I].Width <= ModelChecks[I].Parent.Width);
    if Fits then Description := 'true' else Description := 'false';
    if Metadata <> '' then SaveStringToFile(Metadata,
      '{"dpi":' + IntToStr(WindowDpi(WizardForm.Handle)) +
      ',"model_controls_fit":' + Description +
      ',"viewport_top":' + IntToStr(ModelViewport.Top) +
      ',"viewport_height":' + IntToStr(ModelViewport.Height) +
      ',"notice_height":' + IntToStr(MemoryNotice.Height) +
      ',"skip_top":' + IntToStr(SkipChoice.Top) +
      ',"accuracy_bottom":' + IntToStr(AccuracyNotice.Top + AccuracyNotice.Height) +
      ',"surface_height":' + IntToStr(ModelsPage.SurfaceHeight) +
      ',"font_height":' + IntToStr(WizardForm.Font.Height) + '}', False);
    ImageFile := ExpandConstant('{param:REVIEWBMP|}');
    if ImageFile <> '' then begin
      Bitmap := TBitmap.Create;
      try
        Bitmap.Width := WizardForm.ClientWidth; Bitmap.Height := WizardForm.ClientHeight;
        DC := ReviewDC(WizardForm.Handle);
        try
          if not CopyReviewBitmap(Bitmap.Canvas.Handle, 0, 0, Bitmap.Width, Bitmap.Height,
            DC, 0, 0, $00CC0020) then RaiseException(CustomMessage('ReviewCaptureFailed'));
          Bitmap.SaveToFile(ImageFile);
        finally
          ReleaseReviewDC(WizardForm.Handle, DC);
        end;
      finally
        Bitmap.Free;
      end;
    end;
    Exit;
  end;
  Wanted := ExpandConstant('{param:REVIEWPAGE|welcome}');
  Metadata := ExpandConstant('{param:REVIEWMETA|}');
  if Metadata <> '' then SaveStringToFile(Metadata,
    '{"dpi":' + IntToStr(WindowDpi(WizardForm.Handle)) + '}', False);
  Page := WizardForm.CurPageID;
  if (Wanted = 'uninstall-helper-unavailable') and (Page = ModelsPage.ID) then begin
    ReviewShown := True; ReviewDialogPending := True;
    WizardForm.Show; WizardForm.BringToFront;
    { A dedicated review timer observes our native modal popup. Windows can
      give its sole OK button IDCANCEL (2), allowing Escape to dismiss it. }
    KillTimer(0, Timer);
    Timer := SetTimer(0, 0, 100, CreateCallback(@ReviewPopupTick));
    SavedDpi := SetReviewDpiContext(-4);
    if SavedDpi = 0 then RaiseException(CustomMessage('ReviewDpiFailed'));
    try
      ShowUninstallHelperUnavailable;
    finally
      SetReviewDpiContext(Integer(SavedDpi));
    end;
    Exit;
  end;
  if (Wanted = 'directory') and (Page = ModelsPage.ID) then begin
    { CreateAppDir=no keeps review builds harmless but skips this native page. }
    ReviewShown := True;
    WizardForm.InnerNotebook.ActivePage := WizardForm.SelectDirPage;
    WizardForm.PageNameLabel.Caption := SetupMessage(msgWizardSelectDir);
    Description := SetupMessage(msgSelectDirDesc);
    StringChangeEx(Description, '[name]', 'Dusty', True);
    WizardForm.PageDescriptionLabel.Caption := Description;
    WizardForm.DirEdit.Text := ExpandConstant('{param:DIR|C:\Users\Example\AppData\Local\Programs\Dusty}');
    WizardForm.NextButton.Enabled := True;
    Exit;
  end;
  if ((Wanted = 'welcome') and (Page = wpWelcome)) or
     (((Wanted = 'models') or (Wanted = 'models-low-memory') or
       (Wanted = 'models-bottom') or (Wanted = 'models-checking') or
       (Wanted = 'models-skip')) and (Page = ModelsPage.ID)) or
     ((Wanted = 'directory') and (Page = wpSelectDir)) or
     ((Wanted = 'shortcuts') and (Page = wpSelectTasks)) or
     ((Wanted = 'ready') and (Page = wpReady)) then begin
    ReviewShown := True;
    if Wanted = 'models-low-memory' then MemoryNotice.Caption := CustomMessage('LowMemory');
    if Wanted = 'models-bottom' then ModelViewport.ScrollInView(ModelChecks[GetArrayLength(ModelChecks) - 1].Parent);
    if Wanted = 'models-skip' then begin SkipChoice.Checked := True; SkipModelsClick(nil); end;
    WizardForm.NextButton.Enabled := Wanted <> 'models-checking';
    if Wanted = 'models-checking' then begin
      MemoryNotice.Caption := CustomMessage('CheckingGraphics'); ModelViewport.Enabled := False;
      for I := 0 to GetArrayLength(ModelIds) - 1 do begin
        SetModelChecked(I, False); ModelTitles[I].Caption := ModelLabels[I];
      end;
    end;
    Exit;
  end;
  if (Page = wpLicense) and ((Wanted = 'license') or (Wanted = 'notices') or (Wanted = 'microsoft')) then begin
    ReviewShown := True;
    if Wanted <> 'license' then begin
      Button := TNewButton.Create(WizardForm);
      if Wanted = 'notices' then Button.Tag := 1 else Button.Tag := 2;
      LicenseClick(Button); Button.Free;
    end;
    WizardForm.NextButton.Enabled := False; Exit;
  end;
  if (Page = DownloadPage.ID) and (Wanted <> 'ready') then begin
    ReviewShown := True;
    if Wanted = 'installing' then begin
      WizardForm.InnerNotebook.ActivePage := WizardForm.InstallingPage;
      WizardForm.PageNameLabel.Caption := CustomMessage('InstallFiles');
      WizardForm.PageDescriptionLabel.Caption := CustomMessage('InstallFilesHelp');
      WizardForm.StatusLabel.Caption := CustomMessage('InstallFilesHelp');
      WizardForm.FilenameLabel.Caption := '';
      WizardForm.ProgressGauge.Position := 45;
      WizardForm.NextButton.Visible := False; WizardForm.BackButton.Visible := False;
    end;
    if Wanted = 'finish' then begin
      WizardForm.FinishedLabel.Caption := SuccessText;
      WizardForm.OuterNotebook.ActivePage := WizardForm.FinishedPage;
      WizardForm.NextButton.Caption := SetupMessage(msgButtonFinish);
      WizardForm.NextButton.Enabled := True;
      WizardForm.BackButton.Visible := False; WizardForm.CancelButton.Visible := False;
      WizardForm.RunList.AddCheckBox(CustomMessage('OpenDustyNow'), '', 0, True, True, True, True, nil);
      WizardForm.RunList.Visible := True;
    end;
    if Wanted = 'finish-without' then begin
      WizardForm.FinishedLabel.Caption := CustomMessage('FinishedWithout');
      WizardForm.OuterNotebook.ActivePage := WizardForm.FinishedPage;
      WizardForm.NextButton.Caption := SetupMessage(msgButtonFinish);
      WizardForm.NextButton.Enabled := True;
      WizardForm.BackButton.Visible := False; WizardForm.CancelButton.Visible := False;
      WizardForm.RunList.AddCheckBox(CustomMessage('OpenDustyNow'), '', 0, True, True, True, True, nil);
      WizardForm.RunList.Visible := True;
    end;
    if Wanted = 'uninstall' then InitializeUninstall;
    Exit;
  end;
  if Page = wpLicense then WizardForm.LicenseAcceptedRadio.Checked := True;
  if Page <> wpReady then WizardForm.NextButton.OnClick(WizardForm.NextButton);
end;
#endif

function ShouldSkipPage(Page: Integer): Boolean;
begin
  Result := (Page = DownloadPage.ID) and SilentFailed;
  if Page = ReturnModelsPage.ID then Result := not ReturnModelsRequested;
#ifdef ReviewOnly
  if (Page = DownloadPage.ID) and (ExpandConstant('{param:REVIEWPAGE|}') = 'ready') then Result := True;
#endif
end;

procedure DeinitializeSetup;
begin
#ifndef ReviewOnly
  if not InstallationBegan then
    if not RemoveCrashExclusions(True) then
      SuppressibleMsgBox(CustomMessage('CrashProtectionRemoveFailed'), mbInformation, MB_OK, IDOK);
#endif
  if Timer <> 0 then KillTimer(0, Timer);
  ReleaseChild;
end;
