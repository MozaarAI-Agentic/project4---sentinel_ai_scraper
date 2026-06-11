class FakeRecoveryQueue:
    """Double de test pour RecoveryQueuePort. L'adaptateur Redis réel arrive
    dans un cycle ultérieur (voir ADR-0004)."""

    def __init__(self) -> None:
        self.enqueued_job_ids: list[str] = []

    async def enqueue(self, job_id: str) -> None:
        self.enqueued_job_ids.append(job_id)
