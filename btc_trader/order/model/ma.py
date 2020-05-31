
class MovingAverage:
    """ Moving Average Model """

    def __init__(self,
                 weighted: bool=False,
                 step_size: int=5,
                 trend_trigger_count: int = 3):
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
        flgs = [self.__data_buffer[i] > self.__data_buffer[i + 1] for i in range(len(self.__data_buffer) - 1)]
        return all(flgs[:min(len(flgs), self.__trend_trigger_count)])
        # decreased_count = sum
        # __trend = [int((self.__data_buffer[-i] - self.__data_buffer[- i - 1]) < 0)
        #            for i in range(1, self.__trend_trigger_count)]
        # if sum(__trend) == len(__trend):
        #     return True
        # else:
        #     return False

    def reset_buffer(self):
        self.__pred_buffer = []
        self.__data_buffer = []

    @property
    def data_buffer(self):
        return self.__data_buffer

    @property
    def predict_buffer(self):
        return self.__pred_buffer