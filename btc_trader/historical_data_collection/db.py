"""
Module for database operation
"""

import pandas as pd
from sqlalchemy import Column, DateTime, Float, Integer, String, create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Ticker(Base):
    """Schema"""
    __tablename__ = 'ticker_index'
    ticker_index = Column(Integer, nullable=False, primary_key=True)
    ticker_name = Column(String, nullable=False)


class UpdateTime(Base):
    """Schema"""
    __tablename__ = 'update_time_index'
    ticker_index = Column(Integer, nullable=False, primary_key=True)
    sample_period = Column(Integer, nullable=False, primary_key=True)
    update_unix_time = Column(Integer, nullable=False)
    update_time = Column(DateTime, nullable=False)


class Price(Base):
    """Schema"""
    __tablename__ = 'price'
    ticker_index = Column(Integer, nullable=False, primary_key=True)
    close_unix_time = Column(Integer, nullable=False, primary_key=True)
    sample_period = Column(Integer, nullable=False, primary_key=True)
    open_price = Column(Float, nullable=False)
    high_price = Column(Float, nullable=False)
    low_price = Column(Float, nullable=False)
    close_price = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)


class ConnectPSQL:
    """
    instance to connect postgres DB via sqlalchemy
    """

    def __init__(self, info):
        db = "postgresql+psycopg2://{user}@{host}:{port}/{db}".format(**info)
        self.engine = create_engine(db)
        session = sessionmaker(bind=self.engine)
        self.session = session()

    def create_tables(self):
        Base.metadata.create_all(self.engine)
        self.session.commit()
        self.initializer()

    def show_table_name(self):
        sql = """SELECT relname AS table_name FROM pg_stat_user_tables"""
        return pd.read_sql(sql, self.engine)

    def get_historical_data(self,
                            period,
                            limit=10,
                            begin: int = None,
                            end: int = None):
        """ get latest historical data
        return pandas data-frame with colmuns:
        ['ticker_index', 'close_unix_time', 'sample_period', 'open_price', 'high_price', 'low_price', 'close_price',
        'volume']
        """
        query = "select * from price where sample_period = %i" % period
        if begin is not None:
            query += ' and close_unix_time > %i' % begin
        if end is not None:
            query += ' and close_unix_time < %i' % end
        query += " order by close_unix_time desc"
        if begin is None or end is None:
            query += " limit %i;" % limit
        return pd.read_sql(query, self.engine)

    def initializer(self):
        """ Initialize tables """

        # initialize `last_update`
        tmp = [
            [1, 60, 0, "2000-01-01T00:00:00"],
            [1, 180, 0, "2000-01-01T00:00:00"],
            [1, 300, 0, "2000-01-01T00:00:00"],
            [1, 900, 0, "2000-01-01T00:00:00"],
            [1, 1800, 0, "2000-01-01T00:00:00"],
            [1, 3600, 0, "2000-01-01T00:00:00"],
            [1, 7200, 0, "2000-01-01T00:00:00"],
            [1, 14400, 0, "2000-01-01T00:00:00"],
            [1, 21600, 0, "2000-01-01T00:00:00"],
            [1, 43200, 0, "2000-01-01T00:00:00"],
            [1, 86400, 0, "2000-01-01T00:00:00"],
            [1, 259200, 0, "2000-01-01T00:00:00"],
            [1, 604800, 0, "2000-01-01T00:00:00"]]
        target = pd.DataFrame(tmp, columns=["ticker_index", "sample_period", "update_unix_time", "update_time"])
        target.to_sql(UpdateTime.__tablename__, self.engine, if_exists='replace', index=False)

        # initialize `ticker_index`
        tmp = [[1, "BTCJPY_bF"], [2, "BTCJPY_zaif"]]
        target = pd.DataFrame(tmp, columns=["ticker", "name"])
        target.to_sql(Ticker.__tablename__, self.engine, if_exists='replace', index=False)
