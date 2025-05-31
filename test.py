from passlib.context import CryptContext
pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
for uname in ["ps_user","ts_user","ss_user","sm_user","szip_user","cust_user","mgr_user"]:
    print(uname, pwd_ctx.hash("Пароль123"))