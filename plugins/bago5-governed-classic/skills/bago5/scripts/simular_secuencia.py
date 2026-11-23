"""Recorrer los procedimientos publicados con observaciones simuladas y sin efectos."""
def simulate(catalog, flows, start, observations):
    owners = {row['new_name'] for row in catalog['skills']}
    by_owner = {flow['owner']: flow for flow in flows}
    if start not in owners:
        raise ValueError('responsable desconocido')
    current = start
    seen = set()
    trace = []
    for step in observations:
        if current.startswith('fin:'):
            raise ValueError('observación posterior al cierre')
        if step.get('owner') != current:
            raise ValueError('la observación pertenece a otra responsabilidad')
        observed = step['observed']
        state = (current, observed, step.get('revision'))
        if step.get('stop') or step.get('revoked'):
            target = 'fin:detenido'
        elif state in seen:
            target = 'fin:sin_evidencia_nueva'
        else:
            flow = by_owner.get(current)
            if not flow or observed not in flow['next']:
                raise ValueError('transición sin contrato')
            target = flow['next'][observed]
        seen.add(state)
        if not target.startswith('fin:') and target not in owners:
            raise ValueError('responsable de destino desconocido')
        trace.append({'owner': current, 'observed': observed, 'next': target})
        current = target
    return {'trace': trace, 'result': current, 'terminal': current.startswith('fin:')}
