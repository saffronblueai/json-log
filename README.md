# JSON Log Formatter

This repo defines the JSON log module. This module overrides the python root logger to output logs as json dictionaries. The intent is that this will be used as the default log formatter throughout services .

Clone from open source repository developed by Ben Stovold at saberastronautics: https://bitbucket.org/saberastronautics/jsonlog/src/develop/ 

## Installation

A project using this package should include this line in the requirements file:

```
git@github.com:saffronblueai/json-log.git
```

If the project is using a constraints file to manage private package locations, the requirements file should instead include:

```
jsonlog
```

and the constraints file should include:

```
jsonlog@git@git@github.com:saffronblueai/json-log.git
```

## Example Usage

An example of how to use the logger is shown below. This is an extract from an application using FastAPI, Mangum, and AWS Lambda. In this case, if the application is run locally it will still configure the logger but without the AWS context.

```python
import logging

from fastapi import FastAPI
from jsonlog.utils import configure_logging
from mangum import Mangum

logger = logging.getLogger(__name__)

def get_application() -> FastAPI:
    app = FastAPI()
    if os.getenv("LAMBDA_TASK_ROOT") is None:
        configure_logging()
    return app

app = get_application()

def handler(event, context):
    configure_logging(context)
    logger.info("Called with event", extra=event)
    asgi_handler = Mangum(app)
    return asgi_handler(event, context)
```