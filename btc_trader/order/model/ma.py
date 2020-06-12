
class MovingAverage:
    """ Moving Average Model """

    def __init__(self,
                 weighted: bool=False,
                 step_size: int=5,
                 trend_trigger_window: int = 2,
                 trend_trigger_count: int = 1,
                 trend_trigger_value: int = 0):
        """ Moving Average Model

         Parameter
        -------------
        step_size: int
            step size of moving average
        trend_trigger_count:
            sampling period to calculate moving average
        """

        self.__step_size = step_size
        if weighted:
            norm = sum(list(range(step_size+1)))
            self.__weight = [i/norm for i in reversed(range(1, step_size + 1))]
        else:
            self.__weight = [1.0/step_size] * step_size

        self.__trend_trigger_count = trend_trigger_count
        self.__trend_trigger_window = trend_trigger_window
        self.__trend_trigger_value = trend_trigger_value

        # data buffer for prediction
        self.__data_buffer = []
        self.__pred_buffer = []

    def predict(self, past_data: float):
        """ Prediction """

        # add data to buffer
        self.__data_buffer.append(past_data)

        if len(self.__data_buffer) < self.__step_size:
            # wait until data_buffer store enough data to predict
            return None, None
        elif len(self.__data_buffer) > self.__step_size:
            # keep data buffer size to be not large
            self.__data_buffer = self.__data_buffer[-self.__step_size:]

        data = self.__data_buffer[:- self.__step_size - 1:-1]
        # prediction
        pred = sum([i * w for i, w in zip(data, self.__weight)])
        trend = self.trend()

        return pred, trend

    def trend(self):
        """ if latest data keep decreasing -> regard it as negative trending """
        flgs = [self.__data_buffer[i + 1] - self.__data_buffer[i] < self.__trend_trigger_value
                for i in range(len(self.__data_buffer) - 1)]
        flgs = flgs[-min(self.__trend_trigger_window, len(flgs)):]
        return sum(flgs) >= self.__trend_trigger_count

    def reset_buffer(self):
        self.__pred_buffer = []
        self.__data_buffer = []

    @property
    def data_buffer(self):
        return self.__data_buffer

    @property
    def predict_buffer(self):
        return self.__pred_buffer


if __name__ == '__main__':
    model = MovingAverage(trend_trigger_value=-1)
    for _i in [0, 1, 1, 1, 1, 2, 3, 3, 2, 1, 0, 1, 2, 3, -100, 1, 2, 3]:
        print(_i, model.predict(_i)[1])
