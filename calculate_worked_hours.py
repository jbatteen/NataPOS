def calculate_worked_hours(timesheet):
        del timesheet['username']
        del timesheet['pay_period']
        del timesheet['worked_hours']
        del timesheet['_id']
        timestamps = sorted(timesheet)
        worked_seconds = 0
        worked_hours = 0.0
        last_punch_type = ''
        last_punch_time = 0
        current_punch_type = ''
        number_of_punches = len(timestamps)
        if number_of_punches == 1:
          return 0.0
        count = 0
        for i in timestamps:
          count += 1
          current_punch_type = timesheet[i]
          if count > 1:
            if current_punch_type == 'out' and last_punch_type == 'in':
              worked_seconds = worked_seconds + (int(i) - last_punch_time)
          last_punch_type = current_punch_type
          last_punch_time = int(i)
        worked_hours = float(worked_seconds) / 3600.0
        return worked_hours
