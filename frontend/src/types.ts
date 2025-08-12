export interface User {
  id: string
  email: string
  name: string
  role: 'teacher' | 'student'
}

export interface Teacher extends User {
  role: 'teacher'
  subjects: string[]
}

export interface Student extends User {
  role: 'student'
}

export interface Session {
  id: string
  subject: string
  date: string
  start_time: string
  end_time: string
  meet_link?: string
  status: string
  total_students: number
  teacher_id: string
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
  enrolled_at: string
}