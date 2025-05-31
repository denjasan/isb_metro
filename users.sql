--from passlib.context import CryptContext
--pwd = CryptContext(schemes=["bcrypt"]).hash("ВашАдминПароль")
--print(pwd)

-- Таблица пользователей и их ролей
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(64) UNIQUE NOT NULL,
    password_hash VARCHAR(128) NOT NULL,
    role VARCHAR(32) NOT NULL
);


INSERT INTO users (username, password_hash, role) VALUES
  ('ps_user',   '$2b$12$DQbzcNfIWjqckmsMeiL0JeJ72XS6vaHMxJgC.QJFXikLS8FsmbbVm', 'ПС'),
  ('ts_user',   '$2b$12$3Wum1n.L/N2231XeOra5ze1/EOlI1H0K4L8U1Ss52ilOoLPIsTv82', 'ТС'),
  ('ss_user',   '$2b$12$a0iYm8hZchotSGZU96Y1BOTqHJRuqjQdJfhh719Jfg.bRCq49dCbG', 'СС'),
  ('sm_user',   '$2b$12$N8wEqBntT3jmhZ1wb.3ni.yTGwBPVGREQD6rRCk8CmPzeoCAe/Ps.', 'СМ'),
  ('szip_user', '$2b$12$JNgPY7hT.WcpIT1/Nhg0ZeLW9Tn4Co4kdE0mnsxj1BMpPKhbeVyPy', 'СЗиП'),
  ('cust_user', '$2b$12$z3QGqpSO3.nQaw7FoxYw5uKsBdEftfw6UIanlJgYQ50WZcjFNYIc2', 'Заказчик'),
  ('mgr_user',  '$2b$12$vURpJfHSDQr9Q8SFW3Z9bu2NcayYMbt/ancLbZ2sy6vYLDB9n.6..', 'Руководитель контракта');
