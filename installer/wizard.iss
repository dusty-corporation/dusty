{ Shared production and review page controls. No installer HTTP calls. }
function InitializeUninstall: Boolean; forward;
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
  Action.Visible := False;
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
  Action.Visible := False;
  Phase.Caption := CustomMessage('SetupComplete'); Meter.Position := 100;
  RetryButton.Visible := False; CpuButton.Visible := False; WithoutButton.Visible := False;
  WizardForm.NextButton.Enabled := True;
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
var Code: LongWord; I: Integer; Memory: TMemoryStatus; S: AnsiString;
begin
#ifdef ReviewOnly
  ReviewTick;
  Exit;
#endif
  if (Stage = -1) and (Child.Process <> 0) and (Tick - ProbeBegan > 7000) then begin
    ReleaseChild; ShowMemoryWarning; CheckExistingModels; Exit;
  end;
  if (Child.Process = 0) or (WaitChild(Child.Process, 0) <> 0) then Exit;
  Code := 1; ChildExit(Child.Process, Code); ReleaseChild;
  if Stage = -3 then begin
    if (Code = 0) and LoadStringFromFile(ExpandConstant('{tmp}\model-status.json'), S) then
      for I := 0 to GetArrayLength(ModelIds) - 1 do
        if Pos('"' + ModelIds[I] + '":"damaged"', String(S)) > 0 then
          ModelsPage.CheckListBox.ItemCaption[I] := ModelsPage.CheckListBox.ItemCaption[I] +
            #13#10 + CustomMessage('NeedsDownload');
    Stage := 0; Exit;
  end;
  if Stage = -1 then begin
    MemoryNotice.Caption := '';
    Memory.Length := 64;
    if WinMemoryStatus(Memory) then begin
      if Memory.TotalPhysical < @@MIN_RAM@@ then MemoryNotice.Caption := CustomMessage('LowMemory');
      if (Code = 0) and (Memory.TotalPhysical >= @@MIN_RAM@@) and not ModelsTouched then
        for I := 0 to GetArrayLength(ModelIds) - 1 do begin
          ModelsPage.Values[I] := ModelIds[I] = 'large-v3-turbo-q8_0';
          if ModelsPage.Values[I] then ModelsPage.CheckListBox.ItemCaption[I] := ModelRecommendedLabels[I] + ModelDetails[I]
          else ModelsPage.CheckListBox.ItemCaption[I] := ModelLabels[I] + ModelDetails[I];
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
    DownloadIndex := DownloadIndex + 1;
    Meter.Position := 40 * DownloadIndex div GetArrayLength(Downloads);
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
        '--installer-pass --model ' + Quoted(ModelIds[Selected[0]])) then Failure(True);
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
  Busy := True; DownloadIndex := 0; Stage := -2;
  Meter.Position := 0; Outcome.Caption := '';
  Action.Enabled := False; Action.Visible := False; WizardForm.NextButton.Enabled := False;
  RetryButton.Visible := False; CpuButton.Visible := False; WithoutButton.Visible := False;
  if not StartChild(ExpandConstant('{app}\dusty\dusty.exe'), '--installer-prepare') then Failure(False);
end;

procedure RetryClick(Sender: TObject);
begin
  RetryButton.Visible := False; CpuButton.Visible := False; WithoutButton.Visible := False;
  Busy := True;
  if Stage = 5 then begin
    if not StartChild(ExpandConstant('{app}\dusty\dusty.exe'), '--installer-clear') then Failure(True);
  end else if Stage = 6 then begin
    if not StartChild(ExpandConstant('{app}\dusty\dusty.exe'),
      '--installer-pass --model ' + Quoted(ModelIds[Selected[0]])) then Failure(True);
  end else if Stage >= 3 then begin CpuRetry := False; BeginTest; end else DownloadClick(Sender);
end;

procedure CpuClick(Sender: TObject);
begin
  RetryButton.Visible := False; CpuButton.Visible := False; WithoutButton.Visible := False;
  Busy := True; CpuRetry := True; BeginTest;
end;

procedure CleanupActivePartial;
var File: String;
begin
  if (Stage < -2) or (Stage > 2) or
     (DownloadIndex < 0) or (DownloadIndex >= GetArrayLength(Downloads)) then Exit;
  if Downloads[DownloadIndex] < 0 then File := '@@VAD_FILE@@'
  else File := ModelFiles[Downloads[DownloadIndex]];
  DeleteFile(ExpandConstant('{localappdata}\Dusty\models\') + File + '.part');
end;

procedure WithoutClick(Sender: TObject);
begin
  ReleaseChild;
  CleanupActivePartial;
  Stage := 5;
  if TestFailed then begin
    Busy := StartChild(ExpandConstant('{app}\dusty\dusty.exe'), '--installer-clear');
    if not Busy then begin Failure(True); Exit; end;
  end else begin
    Busy := False; FinishedWithout := True; Phase.Caption := CustomMessage('FinishedWithout');
    WizardForm.NextButton.Enabled := True;
  end;
  Action.Enabled := False; Action.Visible := False; RetryButton.Visible := False;
  CpuButton.Visible := False; WithoutButton.Visible := False;
end;

procedure ModelsClick(Sender: TObject);
begin
  ModelsTouched := True;
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
var I: Integer; Requested: String; Notice: TNewStaticText; Button: TNewButton;
begin
  ModelsPage := CreateInputOptionPage(wpLicense, CustomMessage('ChooseModels'),
    CustomMessage('ChooseModelsHelp'), '', False, True);
  SetArrayLength(ModelIds, @@MODEL_COUNT@@); SetArrayLength(ModelNames, @@MODEL_COUNT@@);
  SetArrayLength(ModelFiles, @@MODEL_COUNT@@); SetArrayLength(ModelLabels, @@MODEL_COUNT@@);
  SetArrayLength(ModelRecommendedLabels, @@MODEL_COUNT@@); SetArrayLength(ModelDetails, @@MODEL_COUNT@@);
  SetArrayLength(ModelBytes, @@MODEL_COUNT@@);
@@MODEL_SETUP@@
  ModelsPage.CheckListBox.OnClickCheck := @ModelsClick;
  ModelsPage.CheckListBox.Height := ModelsPage.SurfaceHeight - ModelsPage.CheckListBox.Top - ScaleY(160);
  Notice := NewLabel(ModelsPage.Surface, 0, 40, @@VOICE_DESCRIPTION@@);
  Notice.Top := ModelsPage.CheckListBox.Top + ModelsPage.CheckListBox.Height + ScaleY(4);
  Notice := NewLabel(ModelsPage.Surface, 0, 45, '@@MODEL_REVIEW@@');
  Notice.Top := ModelsPage.CheckListBox.Top + ModelsPage.CheckListBox.Height + ScaleY(48);
  MemoryNotice := NewLabel(ModelsPage.Surface, 0, 60, '');
  MemoryNotice.Top := Notice.Top + ScaleY(45);
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
  DownloadPage := CreateCustomPage(wpSelectTasks, CustomMessage('DownloadPage'), CustomMessage('DownloadPageHelp'));
#else
  DownloadPage := CreateCustomPage(wpInstalling, CustomMessage('DownloadPage'), CustomMessage('DownloadPageHelp'));
#endif
  Consent := NewLabel(DownloadPage.Surface, 8, 70, '');
  Phase := NewLabel(DownloadPage.Surface, 90, 70, '');
  Meter := TNewProgressBar.Create(WizardForm); Meter.Parent := DownloadPage.Surface;
  Meter.SetBounds(0, ScaleY(170), DownloadPage.SurfaceWidth, ScaleY(24)); Meter.Max := 100;
  Outcome := NewLabel(DownloadPage.Surface, 215, 65, '');
  Action := NewButton(DownloadPage.Surface, 0, 300, 160, CustomMessage('DownloadAction'), @DownloadClick);
  RetryButton := NewButton(DownloadPage.Surface, 0, 300, 110, CustomMessage('Retry'), @RetryClick);
  CpuButton := NewButton(DownloadPage.Surface, 120, 300, 145, CustomMessage('RetryCpu'), @CpuClick);
  WithoutButton := NewButton(DownloadPage.Surface, 275, 300, 200, CustomMessage('FinishWithout'), @WithoutClick);
  RetryButton.Visible := False; CpuButton.Visible := False; WithoutButton.Visible := False;
  Timer := SetTimer(0, 0, 100, CreateCallback(@PollChild));
end;

procedure CurPageChanged(Page: Integer);
var Code: Integer; I: Integer; Mode: String;
begin
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
    Consent.Caption := ConsentText;
    WizardForm.BackButton.Enabled := False;
    WizardForm.NextButton.Enabled := InstallationReady or FinishedWithout;
#ifdef ReviewOnly
    Mode := ExpandConstant('{param:REVIEWSTATE|consent}');
    Phase.Caption := CustomMessage('ReviewOnly');
    Action.Enabled := False; WizardForm.NextButton.Enabled := False;
    if Mode <> 'consent' then Action.Visible := False;
    if Mode = 'download' then begin Phase.Caption := FmtMessage(CustomMessage('DownloadWorking'), [ModelNames[1]]); Meter.Position := 32; end;
    if Mode = 'test' then begin Phase.Caption := FmtMessage(CustomMessage('SelfTestWorking'), [ModelNames[1], '2', '3']); Meter.Position := 70; end;
    if Mode = 'failure' then Failure(False);
    if Mode = 'test-failure' then begin
      Failure(True); Phase.Caption := CustomMessage('GpuSelfTestFailed'); CpuButton.Visible := True;
    end;
    if Mode = 'complete' then FinishReady;
    if Mode = 'without' then begin Phase.Caption := CustomMessage('FinishedWithout'); WithoutButton.Visible := False; end;
    if Mode = 'uninstall' then begin
      Consent.Caption := CustomMessage('RemoveModelsHelp');
      Phase.Caption := FmtMessage(CustomMessage('RemoveModels'), ['1.4']);
    end;
    RetryButton.Enabled := False; CpuButton.Enabled := False; WithoutButton.Enabled := False;
#endif
  end;
  if (Page = wpFinished) and FinishedWithout then WizardForm.FinishedLabel.Caption := CustomMessage('FinishedWithout');
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var I, Count: Integer;
begin
  Result := True;
  if CurPageID = ModelsPage.ID then begin
    Count := 0; for I := 0 to GetArrayLength(ModelIds) - 1 do if ModelsPage.Values[I] then Count := Count + 1;
    Result := Count > 0;
  end;
  if CurPageID = DownloadPage.ID then Result := InstallationReady or FinishedWithout;
#ifdef ReviewOnly
  if CurPageID = DownloadPage.ID then Result := False;
  if CurPageID = wpReady then Result := False;
#endif
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if (CurStep = ssPostInstall) and WizardSilent then begin
    DownloadClick(nil);
    while Busy do begin Sleep(100); PollChild(0, 0, 0, 0); end;
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
  if InstallationReady or FinishedWithout then Result := 0 else Result := 10;
end;

function UninstallModelSize: String;
var Code: Integer; S: AnsiString;
begin
  Result := '0.0';
#ifdef ReviewOnly
  Result := '1.4'; Exit;
#endif
  if Exec(ExpandConstant('{app}\dusty\dusty.exe'), '--model-size --out ' +
    Quoted(ExpandConstant('{tmp}\model-size.txt')), '', SW_HIDE, ewWaitUntilTerminated, Code) then
    if (Code = 0) and LoadStringFromFile(ExpandConstant('{tmp}\model-size.txt'), S) then Result := String(S);
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
      WizardForm.FinishedLabel.Caption := CustomMessage('SetupComplete');
      WizardForm.OuterNotebook.ActivePage := WizardForm.FinishedPage;
      WizardForm.NextButton.Caption := SetupMessage(msgButtonFinish);
      WizardForm.NextButton.Enabled := True;
      WizardForm.BackButton.Visible := False; WizardForm.CancelButton.Visible := False;
    end;
    if Wanted = 'finish-without' then begin
      WizardForm.FinishedLabel.Caption := CustomMessage('FinishedWithout');
      WizardForm.OuterNotebook.ActivePage := WizardForm.FinishedPage;
      WizardForm.NextButton.Caption := SetupMessage(msgButtonFinish);
      WizardForm.NextButton.Enabled := True;
      WizardForm.BackButton.Visible := False; WizardForm.CancelButton.Visible := False;
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
#ifdef ReviewOnly
  if (Page = DownloadPage.ID) and (ExpandConstant('{param:REVIEWPAGE|}') = 'ready') then Result := True;
#endif
end;

procedure DeinitializeSetup;
begin
  if Timer <> 0 then KillTimer(0, Timer);
  ReleaseChild;
end;
