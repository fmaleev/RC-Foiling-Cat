"""Sail Trim add-in: three sliders that trim the RC catamaran rig like a real beach cat.

  Front sail (jib sheet)      -> jib angle
  Back sail (main traveler)   -> boom angle / traveler car position on the rear beam
  Back sail tension (mainsheet) -> leech tension: twist and depth of the main

Button: UTILITIES tab > ADD-INS panel > Sail Trim.
"""
import adsk.core, adsk.fusion, traceback, math

try:
    from . import rig_model as rm
    from . import fusion_rig
except ImportError:
    import rig_model as rm
    import fusion_rig

CMD_ID = 'rcCatSailTrim'
PANEL_ID = 'SolidScriptsAddinsPanel'
_handlers = []


def _app():
    return adsk.core.Application.get()


def _design():
    return adsk.fusion.Design.cast(_app().activeProduct)


def _values(inputs):
    if inputs.itemById('sheet'):  # mini boat: one sail servo
        return rm.single_sheet(math.degrees(inputs.itemById('sheet').valueOne))
    return dict(jib_deg=math.degrees(inputs.itemById('jib').valueOne),
                main_deg=math.degrees(inputs.itemById('main').valueOne),
                tension=float(inputs.itemById('tension').valueOne))


def _readout_text(c):
    r = rm.readout(c)
    if 'boom_angle_deg' in r:
        return ('Boom {boom_angle_deg} deg, jib {jib_angle_deg} deg (jib rides 4 deg wider)\n'
                'Mainsheet: {mainsheet_len_mm} mm   jib sheet: {jib_sheet_len_mm} mm\n'
                'Sail area: main {main_area_m2} m2 + jib {jib_area_m2} m2').format(**r)
    return ('Main twist at head: {twist_top_deg} deg   depth: {main_camber_pct} %\n'
            'Mast rotation: {mast_rotation_deg} deg\n'
            'Traveler car: {traveler_car_y_mm} mm off centre   mainsheet: {mainsheet_len_mm} mm\n'
            'Jib car: {jib_car_y_mm} mm off centre   jib sheet: {jib_sheet_len_mm} mm\n'
            'Sail area: main {main_area_m2} m2 + jib {jib_area_m2} m2').format(**r)


class CreatedHandler(adsk.core.CommandCreatedEventHandler):
    def notify(self, args):
        try:
            design = _design()
            if design is None or fusion_rig.comp_by_name(design.rootComponent, 'Mainsail') is None:
                _app().userInterface.messageBox('Open the RC catamaran design (needs the Mast, Mainsail and Jib components).')
                return
            fusion_rig.use_profile(design)
            c = fusion_rig.read_controls(design)
            cmd = args.command
            inputs = cmd.commandInputs
            if rm.PROFILE == 'mini':
                lo, hi = rm.LIMITS['main_deg']
                s = inputs.addFloatSliderCommandInput('sheet', 'Sails (one sheet servo)', 'deg', math.radians(lo), math.radians(hi))
                s.valueOne = math.radians(c['main_deg'])
                inputs.addTextBoxCommandInput('info', 'Trim', _readout_text(c), 3, True)
                for evt, h in ((cmd.executePreview, PreviewHandler()), (cmd.execute, ExecuteHandler()),
                               (cmd.inputChanged, InputChangedHandler())):
                    evt.add(h)
                    _handlers.append(h)
                return
            lo, hi = rm.LIMITS['jib_deg']
            s = inputs.addFloatSliderCommandInput('jib', 'Front sail (jib sheet)', 'deg', math.radians(lo), math.radians(hi))
            s.valueOne = math.radians(c['jib_deg'])
            lo, hi = rm.LIMITS['main_deg']
            s = inputs.addFloatSliderCommandInput('main', 'Back sail (main traveler)', 'deg', math.radians(lo), math.radians(hi))
            s.valueOne = math.radians(c['main_deg'])
            s = inputs.addIntegerSliderCommandInput('tension', 'Back sail tension (mainsheet %)', 0, 100)
            s.valueOne = int(round(c['tension']))
            inputs.addTextBoxCommandInput('info', 'Trim', _readout_text(c), 5, True)

            for evt, h in ((cmd.executePreview, PreviewHandler()), (cmd.execute, ExecuteHandler()),
                           (cmd.inputChanged, InputChangedHandler())):
                evt.add(h)
                _handlers.append(h)
        except Exception:
            _app().userInterface.messageBox('Sail Trim failed:\n' + traceback.format_exc())


class PreviewHandler(adsk.core.CommandEventHandler):
    def notify(self, args):
        try:
            fusion_rig.update(_design(), _values(args.command.commandInputs))
            args.isValidResult = True
        except Exception:
            _app().userInterface.messageBox('Sail Trim preview failed:\n' + traceback.format_exc())


class ExecuteHandler(adsk.core.CommandEventHandler):
    def notify(self, args):
        try:
            fusion_rig.update(_design(), _values(args.command.commandInputs))
        except Exception:
            _app().userInterface.messageBox('Sail Trim failed:\n' + traceback.format_exc())


class InputChangedHandler(adsk.core.InputChangedEventHandler):
    def notify(self, args):
        try:
            inputs = args.inputs
            box = inputs.itemById('info')
            if box:
                box.text = _readout_text(_values(inputs))
        except Exception:
            pass


def run(context):
    try:
        ui = _app().userInterface
        old = ui.commandDefinitions.itemById(CMD_ID)
        if old:
            old.deleteMe()
        cmd_def = ui.commandDefinitions.addButtonDefinition(
            CMD_ID, 'Sail Trim', 'Trim the catamaran sails: jib sheet, main traveler, mainsheet tension.')
        h = CreatedHandler()
        cmd_def.commandCreated.add(h)
        _handlers.append(h)
        panel = ui.allToolbarPanels.itemById(PANEL_ID)
        ctrl = panel.controls.itemById(CMD_ID)
        if ctrl:
            ctrl.deleteMe()
        panel.controls.addCommand(cmd_def)
    except Exception:
        _app().userInterface.messageBox('Sail Trim add-in failed to start:\n' + traceback.format_exc())


def stop(context):
    try:
        ui = _app().userInterface
        panel = ui.allToolbarPanels.itemById(PANEL_ID)
        ctrl = panel.controls.itemById(CMD_ID) if panel else None
        if ctrl:
            ctrl.deleteMe()
        d = ui.commandDefinitions.itemById(CMD_ID)
        if d:
            d.deleteMe()
        _handlers.clear()
    except Exception:
        pass
