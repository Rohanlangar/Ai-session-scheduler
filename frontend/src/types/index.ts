export interface Teacher {
  id: string
  name: string
  email: string
  subjects: string[]
}

export interface Student {
  id: string
  name: string
  email: string
}

export interface Session {
  id: string
  teacher_id: string
  subject: string
  date: string
  start_time: string
  end_time: string
  meet_link: string
  status: string
  total_students: number
}

export interface TeacherAvailability {
  id: string
  teacher_id: string
  date: string
  start_time: string
  end_time: string
  subject: string
}

export interface SessionEnrollment {
  id: string
  session_id: string
  student_id: string
}