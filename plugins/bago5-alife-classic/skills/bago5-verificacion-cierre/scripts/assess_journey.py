"""Contrasta un plan de aceptación y sus recibos. Solo lee los dos JSON indicados."""
import argparse
import json
import sys
from pathlib import Path


MODES = {"page": {"live_http", "live_interaction"},
         "action": {"live_interaction"}, "write": {"live_interaction"},
         "reread": {"live_interaction"}}


def required_text(record, name):
    value = record.get(name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Campo de texto obligatorio: {name}")
    return value


def assess(plan, receipts):
    if not isinstance(plan, dict) or not isinstance(receipts, list):
        raise ValueError("Se requieren un plan y una lista de recibos.")
    destination = required_text(plan, "destination")
    candidate = required_text(plan, "candidate")
    steps = plan.get("steps")
    if not isinstance(steps, list) or not steps:
        raise ValueError("El plan debe enumerar los hitos solicitados.")

    observed = {}
    receipt_ids = set()
    for receipt in receipts:
        if not isinstance(receipt, dict):
            raise ValueError("Recibo inválido.")
        step = required_text(receipt, "step")
        identity = required_text(receipt, "id")
        if step in observed or identity in receipt_ids:
            raise ValueError("Selecciona un solo intento por hito con identificadores únicos.")
        observed[step] = receipt
        receipt_ids.add(identity)

    results = {}
    for step in steps:
        if not isinstance(step, dict):
            raise ValueError("Hito inválido.")
        key = required_text(step, "step")
        role = required_text(step, "role")
        resource = required_text(step, "resource")
        expected = required_text(step, "expect")
        kind = required_text(step, "kind")
        if kind not in MODES or key in results:
            raise ValueError(f"Hito duplicado o tipo desconocido: {key}")
        after = step.get("after")
        if after is not None and (not isinstance(after, str) or after not in results):
            raise ValueError(f"Debe declararse primero el hito precedente de {key}.")
        receipt = observed.get(key)
        if kind == "write" and step.get("write_authorized") is not True:
            if receipt and receipt.get("result") != "NOT_RUN":
                state, reason = "OUT_OF_SCOPE", "El recibo declara una acción fuera del alcance autorizado."
            else:
                state, reason = "NOT_RUN", "Escritura fuera del alcance autorizado."
        elif receipt is None:
            state, reason = "NOT_RUN", "Falta el recibo del hito."
        elif receipt.get("result") in ("FAIL", "NOT_RUN", "INCONCLUSIVE"):
            state, reason = receipt["result"], str(receipt.get("reason") or "Sin comprobación satisfactoria.")
        elif receipt.get("result") != "PASS":
            state, reason = "INCONCLUSIVE", "Resultado desconocido."
        elif (receipt.get("destination"), receipt.get("candidate"), receipt.get("role"),
              receipt.get("resource")) != (destination, candidate, role, resource):
            state, reason = "INCONCLUSIVE", "Destino, candidata, rol o recurso distintos."
        elif receipt.get("mode") not in MODES[kind] or receipt.get("operation") != kind:
            state, reason = "INCONCLUSIVE", "El medio de prueba no demuestra este hito."
        elif not all(isinstance(receipt.get(field), str) and receipt[field].strip()
                     for field in ("run", "evidence", "observed")):
            state, reason = "INCONCLUSIVE", "Falta ejecución, evidencia o resultado observado."
        elif receipt["observed"] != expected:
            state, reason = "FAIL", "La observación no coincide con el resultado esperado."
        elif after is not None and (
            results[after]["state"] != "PASS" or receipt.get("previous_receipt") != observed[after]["id"]
            or receipt["run"] != observed[after].get("run")
        ):
            state, reason = "INCONCLUSIVE", "Recorrido consecutivo sin demostrar."
        else:
            state, reason = "PASS", "Recibo aplicable al hito."
        results[key] = {"state": state, "reason": reason}
    missing = [key for key, result in results.items() if result["state"] != "PASS"]
    state = "VERIFIED"
    if missing:
        state = "BLOQUEADO" if len(missing) == len(results) else "PARCIAL"
    return {"state": state, "scope": "receipt_consistency_only", "unmet": missing, "steps": results}


def load(path):
    with path.open("rb") as stream:
        content = stream.read(2 * 1024 * 1024 + 1)
    if len(content) > 2 * 1024 * 1024:
        raise ValueError("JSON supera el límite de 2 MiB.")
    return json.loads(content.decode("utf-8-sig"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    parser.add_argument("receipts", type=Path)
    args = parser.parse_args()
    try:
        result = assess(load(args.plan), load(args.receipts))
    except (ValueError, OSError, RecursionError) as error:
        print(json.dumps({"state": "BLOQUEADO", "reason": str(error)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["state"] == "VERIFIED" else 1


if __name__ == "__main__":
    sys.exit(main())
