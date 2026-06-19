import asyncio

from bot.handlers.commands import _reply_photo, _reply_text


class DummyMessage:
    def __init__(self) -> None:
        self.text_replies: list[str] = []
        self.photo_replies: list[tuple[object, str]] = []

    async def reply_text(self, text: str) -> None:
        self.text_replies.append(text)

    async def reply_photo(self, *, photo, caption: str) -> None:
        self.photo_replies.append((photo, caption))


class DummyUpdate:
    def __init__(self, effective_message) -> None:
        self.effective_message = effective_message


def test_reply_text_uses_effective_message() -> None:
    async def run_case() -> None:
        message = DummyMessage()
        update = DummyUpdate(message)

        sent = await _reply_text(update, "hello")

        assert sent is True
        assert message.text_replies == ["hello"]

    asyncio.run(run_case())


def test_reply_photo_uses_effective_message() -> None:
    async def run_case() -> None:
        message = DummyMessage()
        update = DummyUpdate(message)

        sent = await _reply_photo(update, photo="photo-bytes", caption="chart")

        assert sent is True
        assert message.photo_replies == [("photo-bytes", "chart")]

    asyncio.run(run_case())


def test_reply_text_without_effective_message_returns_false() -> None:
    async def run_case() -> None:
        update = DummyUpdate(None)

        sent = await _reply_text(update, "hello")

        assert sent is False

    asyncio.run(run_case())
