# Autoloader (removed)

`AudioStreamAutoloader` let this service pull a stream directly from another microservice's URL
(`AUTOLOAD_STREAM_URL`), bypassing Brain. It was removed because Brain is the only coordinator between
microservices, the option was unset in every shipped configuration, its only effect was to log
the result, and both neighbours now speak the contract event streams, not the raw bytes it read.
The last version of the code is kept next to this note as `audio_stream_autoloader.py.txt`.
