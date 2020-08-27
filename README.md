Websockets Monitor Lambda - Monitors websockets and websockets-emitter based up on respective
health checks

Lambda Environment: Python3.8
Environment Variables:
* SNS_ARN    - ARN of SNS topic where the alerts to be published. 
               Lambda's role should have sns:publish permission to this topic.
* URL_WS_*   - Websocket url to be monitored. Each environment should have one environment 
               variable in URL_WS_<environment name> format
* URL_WSE_*  - Websockets-emitter url to be monitored. Each environment should have one 
               environment variable in URL_WSE_<environment name> format
