# RC4: incidencias y estado

P0/P1 se reprodujeron en RC3 y su NO_GO se conserva como antecedente. RC4 incorpora IPC independiente de SQLite, latch previo durable, exclusion de propietarios y recuperacion individual explicitamente solicitada. El launcher agrega fallback python (P2).

La implementacion no constituye por si sola PASS. El informe que acompana el ZIP final identifica hashes, pruebas ejecutadas, verificacion independiente y NOT_RUN. Los recibos historicos RC2/RC3 no se reutilizan como evidencia funcional RC4.
