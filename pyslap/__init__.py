import asyncio
import io
import os
import time
import typing
import logging
import base64
import arsenic
import structlog  # arsenic uses this
import aiohttp.web
import contextlib


async def index(request):
    encoded = base64.b64encode(request.app.screenshot_io.read()).decode()
    body = """
    <html>
        <img src="data:image/png;base64,{screenshot}"/>
    </html>
    """.format(
        screenshot=encoded
    ).strip()
    return aiohttp.web.Response(body=body, content_type="text/html")


def make_application(driver):
    application = aiohttp.web.Application()
    application.add_routes(
        [
            aiohttp.web.get("/", index),
        ]
    )
    application.driver = driver
    return application


@contextlib.asynccontextmanager
async def run_browser() -> typing.AsyncContextManager[arsenic.Session]:
    service = arsenic.services.Geckodriver(log_file=os.devnull)
    browser = arsenic.browsers.Firefox()
    async with arsenic.get_session(service, browser) as driver:
        yield driver


async def get_screenshot(driver: arsenic.Session) -> io.BytesIO:
    screenshot = await driver.get_screenshot()
    return screenshot


async def run(*, port):
    async with run_browser() as driver:
        await driver.get("http://example.org")
        application = make_application(driver)
        runner = aiohttp.web.AppRunner(application)
        await runner.setup()
        server = aiohttp.web.TCPSite(runner, port=port)
        await server.start()
        try:
            while True:
                before_screenshot = time.time()
                application.screenshot_io = await get_screenshot(driver)
                after_screenshot = time.time()
                delay = after_screenshot - before_screenshot
                await asyncio.sleep(1 - delay)
        except KeyboardInterrupt:
            await server.stop()


def set_arsenic_log_level(level=logging.WARNING):
    # Create logger
    logger = logging.getLogger("arsenic")

    # We need factory, to return application-wide logger
    def logger_factory():
        return logger

    structlog.configure(logger_factory=logger_factory)
    logger.setLevel(level)


if __name__ == "__main__":
    set_arsenic_log_level()
    asyncio.run(run(port=8080))
