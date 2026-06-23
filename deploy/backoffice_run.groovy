pipeline {
    agent any
    parameters {
        string(name: 'TAG', defaultValue: 'latest', description: 'Run 할 이미지 태그')
        string(name: 'IP', defaultValue: 'x.x.x.x(APP_SERVER)', description: 'default : 백오피스 서버')
    }
    stages {
        stage('1. Docker Run') {
            steps {
                withCredentials([
                    sshUserPrivateKey(
                        credentialsId: 'ssh_jenkins',
                        keyFileVariable: 'SSH_KEY'
                    ),
                    usernamePassword(credentialsId: 'admin',
                        usernameVariable: 'HB_USER',
                        passwordVariable: 'HB_PW'),
                    usernamePassword(credentialsId: 'Git_account',
                        usernameVariable: 'GIT_USER',
                        passwordVariable: 'GIT_TOKEN'),
                ]) {
                    sh """
                        ssh -i ${SSH_KEY} -p 50022 -o StrictHostKeyChecking=no jenkins@${params.IP} '
                            export XDG_RUNTIME_DIR=/run/user/\$(id -u)

                            echo "===== 작업 디렉토리로 이동 ====="
                            cd /home/jenkins/backoffice
                            pwd
                            hostname

                            echo "===== Git pull (docker-compose.yml 최신화) ====="
                            git pull http://${GIT_USER}:${GIT_TOKEN}@x.x.x.x(GIT_SERVER)/ncdc-source-code/ncdc-backoffice.git main

                            echo "===== Harbor 로그인 ====="
                            echo "${HB_PW}" | docker login x.x.x.x(HARBOR_URL) \
                                --username "${HB_USER}" \
                                --password-stdin

                            echo "===== docker compose down ====="
                            docker compose down || true

                            echo "===== docker pull ====="
                            docker pull x.x.x.x(HARBOR_URL)/dev/jira-reporter-frontend:${params.TAG}
                            docker pull x.x.x.x(HARBOR_URL)/dev/jira-reporter-backend:${params.TAG}
                            docker pull x.x.x.x(HARBOR_URL)/dev/mongo:latest
                            docker pull x.x.x.x(HARBOR_URL)/dev/mongo-express:latest

                            echo "===== docker compose up ====="
                            TAG=${params.TAG} docker compose up -d --no-build

                            sleep 10
                            docker ps
                        '
                    """
                }
            }
        }
    }
    post {
        success {
            echo "성공."
        }
        failure {
            echo "실패"
        }
    }
}