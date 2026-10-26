"""Start the local app. ChineseModels is poll-based, so no callback tunnel is needed."""
import os
import uvicorn

if __name__=='__main__':
    uvicorn.run('app:app',host='127.0.0.1',port=int(os.getenv('PORT','8770')))
