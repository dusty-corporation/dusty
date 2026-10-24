{ Shared production and review page controls. No installer HTTP calls. }
function InitializeUninstall: Boolean; forward;
procedure FinishStopped; forward;
procedure StopModelSetup(Confirm: Boolean); forward;
#ifdef ReviewOnly
procedure ReviewTick; forward;
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

function NewButton(Parent: TWinControl; Left, Top, Width: Integer; Text: String;
  Handler: TNotifyEvent): TNewButton;
begin
  Result := TNewButton.Create(WizardForm);
  Result.Parent := Parent;
  Result.SetBounds(ScaleX(Left), ScaleY(Top), ScaleX(Width), ScaleY(32));
  Result.Caption := Text;
  Result.OnClick := Handler;
end;

function ConsentText: String;
var I, Mask, Bit: Integer;
begin
  Mask := 0; Bit := 1;
  for I := 0 to GetArrayLength(ModelIds) - 1 do begin
    if ModelsPage.Values[I] then Mask := Mask + Bit;
    Bit := Bit * 2;
  end;
  Result := '';
  case Mask of
@@CONSENT_CASES@@
  end;
end;

function DownloadText: String;
var I, Mask, Bit: Integer;
begin
  Mask := 0; Bit := 1;
  for I := 0 to GetArrayLength(ModelIds) - 1 do begin
    if ModelsPage.Values[I] then Mask := Mask + Bit;
    Bit := Bit * 2;
  end;
  Result := '';
  case Mask of
@@DOWNLOAD_CASES@@
  end;
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
  if (Stage >= 0) and (Stage <= 2) and (DownloadIndex < GetArrayLength(Downloads)) then begin
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
  Info[17] := $20;
  ChildJob := WinCreateJob(0, 0);
  Result := (ChildJob <> 0) and WinSetJob(ChildJob, 9, Info, 112);
  for I := 0 to 67 do Startup[I] := 0;
  Startup[0] := 68;
  if Result then Result := CreateChild(0, Quoted(Exe) + ' ' + Arguments,
    0, 0, False, $08000004, 0, ExpandConstant('{tmp}'), Startup, Child);
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
  if IsTest then
    if LoadStringFromFile(ExpandConstant('{tmp}\test-result.txt'), S) then
      GpuFailed := Pos('VULKAN', String(S)) > 0;
  if IsTest and GpuFailed then Phase.Caption := CustomMessage('GpuSelfTestFailed')
  else if IsTest then Phase.Caption := CustomMessage('SelfTestFailed')
  else Phase.Caption := CustomMessage('DownloadFailed');
  RetryButton.Visible := True;
  CpuButton.Visible := IsTest and GpuFailed;
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
var Memory: TMemoryStatus;
begin
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

procedure PollChild(A, B, C, D: LongWord);
var Code: LongWord; I: Integer; Memory: TMemoryStatus; S: AnsiString; Prefix, Expected: Int64; Part: String;
begin
#ifdef ReviewOnly
  ReviewTick;
  Exit;
#endif
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
  if (Child.Process = 0) or (WaitChild(Child.Process, 0) <> 0) then Exit;
  Code := 1; ChildExit(Child.Process, Code); ReleaseChild;
  if Stage = -3 then begin
    if (Code = 0) and LoadStringFromFile(ExpandConstant('{tmp}\model-status.json'), S) then
      for I := 0 to GetArrayLength(ModelIds) - 1 do
        if Pos('"' + ModelIds[I] + '":"damaged"', String(S)) > 0 then
          ModelsPage.CheckListBox.ItemCaption[I] := ModelsPage.CheckListBox.ItemCaption[I] + #13#10 + CustomMessage('NeedsDownload');
    Stage := 0; Exit;
  end;
  if Stage = -1 then begin
    MemoryNotice.Caption := '';
    Memory.Length := 64;
    if WinMemoryStatus(Memory) then begin
      if Memory.TotalPhysical < @@MIN_RAM@@ then MemoryNotice.Caption := CustomMessage('LowMemory');
      if (Code = 0) and (Memory.TotalPhysical >= @@MIN_RAM@@) then
      begin
        RecommendedModel := 'large-v3-turbo-q8_0';
        for I := 0 to GetArrayLength(ModelIds) - 1 do begin
          if not ModelsTouched then ModelsPage.Values[I] := ModelIds[I] = 'large-v3-turbo-q8_0';
          if ModelIds[I] = 'large-v3-turbo-q8_0' then ModelsPage.CheckListBox.ItemCaption[I] := ModelRecommendedLabels[I] + ModelDetails[I]
          else ModelsPage.CheckListBox.ItemCaption[I] := ModelLabels[I] + ModelDetails[I];
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
    if (Stage = 0) and (Code <> 0) then begin Stage := 1; BeginFetch('download'); Exit; end;
    if Code <> 0 then begin Failure(False); Exit; end;
    if Stage = 1 then begin Stage := 2; BeginFetch('verify'); Exit; end;
    if Downloads[DownloadIndex] < 0 then CompletedModelBytes := CompletedModelBytes + @@VAD_BYTES@@
    else CompletedModelBytes := CompletedModelBytes + ModelBytes[Downloads[DownloadIndex]];
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
  SetArrayLength(Selected, 0); Smallest := -1;
  for I := 0 to GetArrayLength(ModelIds) - 1 do if ModelsPage.Values[I] then begin
    Count := GetArrayLength(Selected); SetArrayLength(Selected, Count + 1); Selected[Count] := I;
    if Smallest < 0 then Smallest := I
    else if ModelBytes[I] < ModelBytes[Smallest] then Smallest := I;
  end;
  if GetArrayLength(Selected) = 0 then Exit;
  SetArrayLength(Downloads, GetArrayLength(Selected) + 1);
  for I := 0 to GetArrayLength(Selected) - 1 do Downloads[I] := Selected[I];
  Downloads[GetArrayLength(Selected)] := -1;
  TotalModelBytes := @@VAD_BYTES@@; CompletedModelBytes := 0;
  for I := 0 to GetArrayLength(Selected) - 1 do
    TotalModelBytes := TotalModelBytes + ModelBytes[Selected[I]];
  DownloadStarted := True; Consent.Caption := DownloadText;
  Meter.Visible := True; Amount.Visible := True;
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
    ExpandConstant('{app}'), SW_HIDE, ewWaitUntilTerminated, Code);
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
  ModelsTouched := True;
  ShowMemoryWarning;
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
  RecommendedModel := 'small';
  ModelsPage := CreateInputOptionPage(wpLicense, CustomMessage('ChooseModels'),
    CustomMessage('ChooseModelsHelp'), '', False, True);
  SetArrayLength(ModelIds, @@MODEL_COUNT@@); SetArrayLength(ModelNames, @@MODEL_COUNT@@);
  SetArrayLength(ModelFiles, @@MODEL_COUNT@@); SetArrayLength(ModelLabels, @@MODEL_COUNT@@);
  SetArrayLength(ModelRecommendedLabels, @@MODEL_COUNT@@); SetArrayLength(ModelDetails, @@MODEL_COUNT@@);
  SetArrayLength(ModelBytes, @@MODEL_COUNT@@);
@@MODEL_SETUP@@
  ModelsPage.CheckListBox.OnClickCheck := @ModelsClick;
  ModelsPage.CheckListBox.Height := ModelsPage.SurfaceHeight - ModelsPage.CheckListBox.Top - ScaleY(160);
  VoiceNotice := NewLabel(ModelsPage.Surface, 0, 40, @@VOICE_DESCRIPTION@@);
  VoiceNotice.Top := ModelsPage.CheckListBox.Top + ModelsPage.CheckListBox.Height + ScaleY(4);
  AccuracyNotice := NewLabel(ModelsPage.Surface, 0, 45, '@@MODEL_REVIEW@@');
  AccuracyNotice.Top := ModelsPage.CheckListBox.Top + ModelsPage.CheckListBox.Height + ScaleY(48);
  MemoryNotice := NewLabel(ModelsPage.Surface, 0, 60, '');
  MemoryNotice.Top := AccuracyNotice.Top + ScaleY(45);
  Requested := ExpandConstant('{param:MODELS|small}');
  for I := 0 to GetArrayLength(ModelIds) - 1 do begin
    ModelsPage.Values[I] := Pos(',' + ModelIds[I] + ',', ',' + Requested + ',') > 0;
    if ModelIds[I] = 'small' then ModelsPage.CheckListBox.ItemCaption[I] := ModelRecommendedLabels[I] + ModelDetails[I];
  end;
  ModelsTouched := ExpandConstant('{param:MODELS|}') <> '';
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

procedure CurPageChanged(Page: Integer);
var Code: Integer; I, Count: Integer; Mode: String;
begin
  if Page = ReturnModelsPage.ID then begin
    EnableModelPageCancel;
    ModelsPage.CheckListBox.Parent := ReturnModelsPage.Surface;
    VoiceNotice.Parent := ReturnModelsPage.Surface;
    AccuracyNotice.Parent := ReturnModelsPage.Surface;
    MemoryNotice.Parent := ReturnModelsPage.Surface;
  end;
  if (Page = ModelsPage.ID) and not ProbeStarted then begin
    ProbeStarted := True;
#ifndef ReviewOnly
    MemoryNotice.Caption := CustomMessage('CheckingGraphics');
    try ExtractTemporaryFiles('{tmp}\probe\*');
    except ShowMemoryWarning; Exit; end;
    ProbeRoot := ExpandConstant('{tmp}\probe');
    Stage := -1; ProbeBegan := Tick;
    if not StartChild(ProbeRoot + '\dusty\dusty.exe', '--probe-vulkan --out ' +
      Quoted(ExpandConstant('{tmp}\probe-result.json'))) then Stage := 0;
#endif
  end;
  if Page = DownloadPage.ID then begin
    EnableModelPageCancel;
    WizardForm.BackButton.Visible := True;
    WizardForm.BackButton.Enabled := not DownloadStarted;
    WizardForm.NextButton.Enabled := not DownloadStarted or InstallationReady or FinishedWithout;
    if DownloadStarted then begin
      Consent.Caption := DownloadText;
      WizardForm.NextButton.Caption := SetupMessage(msgButtonNext);
    end else begin
      Consent.Caption := ConsentText;
      WizardForm.NextButton.Caption := CustomMessage('DownloadAction');
    end;
    Meter.Visible := DownloadStarted; Amount.Visible := DownloadStarted;
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
        if ModelsPage.Values[I] then begin
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
    if StopRequested then
      for I := 0 to WizardForm.RunList.Items.Count - 1 do WizardForm.RunList.Checked[I] := False;
    if FinishedWithout then WizardForm.FinishedLabel.Caption := CustomMessage('FinishedWithout')
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
    Count := 0; for I := 0 to GetArrayLength(ModelIds) - 1 do if ModelsPage.Values[I] then Count := Count + 1;
    Result := Count > 0;
    if not Result then MemoryNotice.Caption := CustomMessage('NeedModel');
    if Result then ReturnModelsRequested := False;
  end;
  if CurPageID = DownloadPage.ID then begin
    Result := InstallationReady or FinishedWithout;
#ifndef ReviewOnly
    if not DownloadStarted then begin DownloadClick(nil); Result := False; end;
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
        '--installer-upgrade-root ' + Quoted(ExpandConstant('{app}')), '', SW_HIDE,
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
    DownloadClick(nil);
    while Busy do begin Sleep(100); PollChild(0, 0, 0, 0); end;
    if StopRequested then Exit;
    if not InstallationReady then RaiseException(CustomMessage('SelfTestFailed'));
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
procedure ReviewTick;
var Wanted, Metadata, Description: String; Page: Integer; Button: TNewButton;
begin
  if ReviewShown then Exit;
  Wanted := ExpandConstant('{param:REVIEWPAGE|welcome}');
  Metadata := ExpandConstant('{param:REVIEWMETA|}');
  if Metadata <> '' then SaveStringToFile(Metadata,
    '{"dpi":' + IntToStr(WindowDpi(WizardForm.Handle)) + '}', False);
  Page := WizardForm.CurPageID;
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
     (((Wanted = 'models') or (Wanted = 'models-low-memory')) and (Page = ModelsPage.ID)) or
     ((Wanted = 'directory') and (Page = wpSelectDir)) or
     ((Wanted = 'shortcuts') and (Page = wpSelectTasks)) or
     ((Wanted = 'ready') and (Page = wpReady)) then begin
    ReviewShown := True;
    if Wanted = 'models-low-memory' then MemoryNotice.Caption := CustomMessage('LowMemory');
    WizardForm.NextButton.Enabled := True; Exit;
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
  Result := False;
  if Page = ReturnModelsPage.ID then Result := not ReturnModelsRequested;
#ifdef ReviewOnly
  if (Page = DownloadPage.ID) and (ExpandConstant('{param:REVIEWPAGE|}') = 'ready') then Result := True;
#endif
end;

procedure DeinitializeSetup;
begin
  if Timer <> 0 then KillTimer(0, Timer);
  ReleaseChild;
end;
