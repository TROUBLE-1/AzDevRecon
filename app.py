from AzDevRecon import app, socketio

if '__main__' == __name__:
    socketio.run(app, host='0.0.0.0', port=80, debug=True)