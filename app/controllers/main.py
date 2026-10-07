import wave
from flask import Blueprint, Response, jsonify, render_template, request

from app.models.emulator import emulator

bp = Blueprint('main', __name__)


@bp.get('/')
def index():
    return render_template('index.html')


@bp.get('/healthz')
def healthz():
    return jsonify({'status': 'ok', 'machine': 'CCE MC-1000', 'pc': emulator.machine.cpu.pc})


@bp.get('/api/state')
def state():
    return jsonify(emulator.machine.snapshot())


@bp.post('/api/key')
def key():
    d = request.get_json(force=True)
    emulator.machine.key(str(d.get('key', '')), bool(d.get('down', True)))
    return ('', 204)


@bp.post('/api/type')
def type_text():
    d = request.get_json(force=True)
    emulator.machine.type_text(str(d.get('text', '')))
    return ('', 204)


@bp.post('/api/reset')
def reset():
    emulator.machine.reset()
    emulator.machine.run_for(0.5)
    return ('', 204)


@bp.post('/api/cassette/load')
def cassette_load():
    try:
        f = request.files['file']
        emulator.machine.load_wav(f.read())
        return ('', 204)
    except (KeyError, ValueError, EOFError, wave.Error) as exc:
        return jsonify({'error': str(exc)}), 400


@bp.post('/api/cassette/record/start')
def cassette_record_start():
    emulator.machine.begin_record()
    return ('', 204)


@bp.post('/api/cassette/record/stop')
def cassette_record_stop():
    data = emulator.machine.end_record_wav()
    return Response(
        data,
        mimetype='audio/wav',
        headers={'Content-Disposition': 'attachment; filename=mc1000-save.wav'},
    )


@bp.get('/api/printer')
def printer_output():
    data = bytes(emulator.machine.printer_output)
    return Response(
        data,
        mimetype='application/octet-stream',
        headers={'Content-Disposition': 'attachment; filename=mc1000-printer.bin'},
    )
